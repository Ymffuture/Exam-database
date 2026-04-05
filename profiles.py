from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from auth import get_current_user
from models import ProfileCreate, ProfileUpdate, ProfileOut
from datetime import datetime

router = APIRouter(prefix="/profiles", tags=["profiles"])


def serialize_profile(p: dict) -> dict:
    p.pop("_id", None)
    return p


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    profile = await db.profiles.find_one({"user_id": current_user["user_id"]})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return serialize_profile(profile)


@router.post("/me", response_model=ProfileOut, status_code=201)
async def create_my_profile(
    body: ProfileCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    existing = await db.profiles.find_one({"user_id": current_user["user_id"]})
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")

    now = datetime.utcnow().isoformat()
    doc = {
        "user_id": current_user["user_id"],
        "full_name": body.full_name,
        "date_of_birth": body.date_of_birth,
        "avatar_url": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.profiles.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/me", response_model=ProfileOut)
async def update_my_profile(
    body: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.utcnow().isoformat()
    result = await db.profiles.find_one_and_update(
        {"user_id": current_user["user_id"]},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    result.pop("_id", None)
    return result
