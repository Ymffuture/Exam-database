from datetime import datetime, timedelta
from typing import Optional
import httpx
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_settings, get_db

security = HTTPBearer()


def create_access_token(data: dict) -> str:
    settings = get_settings()
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload["exp"] = expire
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def verify_google_token(id_token: str) -> dict:
    """Verify a Google ID token and return user info."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        data = resp.json()
        if "error" in data:
            raise HTTPException(status_code=401, detail=data.get("error_description", "Invalid token"))
        return data


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    """Exchange Google auth code for tokens and return user info."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to exchange Google code")

        tokens = token_resp.json()
        id_token = tokens.get("id_token")
        if not id_token:
            raise HTTPException(status_code=401, detail="No ID token in response")

        # Verify and decode the ID token
        user_info = await verify_google_token(id_token)
        return user_info


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> dict:
    """Dependency: decode JWT and return the user document from DB."""
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"user_id": user_id, "email": payload.get("email", "")}


async def require_admin(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Dependency: ensure the current user is an admin."""
    role = await db.user_roles.find_one(
        {"user_id": current_user["user_id"], "role": "admin"}
    )
    if not role:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
