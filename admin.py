from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from auth import require_admin, get_current_user
from models import AdminSettingsUpdate, AdminSettingsOut
from datetime import datetime
import uuid

router = APIRouter(prefix="/admin", tags=["admin"])

# All 4 subjects must be visible to admin - no subject filtering
ALL_SUBJECTS = ["math", "physics", "english", "life-sciences"]


@router.get("/settings", response_model=AdminSettingsOut)
async def get_settings(
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    s = await db.admin_settings.find_one({})
    if not s:
        # Create defaults
        defaults = {
            "id": str(uuid.uuid4()),
            "unlock_wait_minutes": 1440,
            "passing_percentage": 70,
            "per_question_minutes": 3,
            "total_duration_minutes": 90,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await db.admin_settings.insert_one(defaults)
        defaults.pop("_id", None)
        return defaults
    s.pop("_id", None)
    return s


@router.patch("/settings", response_model=AdminSettingsOut)
async def update_settings(
    body: AdminSettingsUpdate,
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow().isoformat()

    s = await db.admin_settings.find_one({})
    if not s:
        raise HTTPException(status_code=404, detail="Settings not found")

    result = await db.admin_settings.find_one_and_update(
        {"_id": s["_id"]},
        {"$set": updates},
        return_document=True,
    )
    result.pop("_id", None)
    return result


@router.get("/students")
async def list_students(
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    """
    Returns all students with their sessions for ALL 4 subjects.
    FIX: No subject filtering - admin sees english + life-sciences too.
    """
    profiles_cursor = db.profiles.find({})
    profiles = []
    async for p in profiles_cursor:
        p.pop("_id", None)
        profiles.append(p)

    # Fetch ALL sessions regardless of subject
    sessions_cursor = db.exam_sessions.find({})
    sessions_by_user: dict = {}
    async for s in sessions_cursor:
        s.pop("_id", None)
        uid = s["user_id"]
        if uid not in sessions_by_user:
            sessions_by_user[uid] = []
        sessions_by_user[uid].append(s)

    result = []
    for p in profiles:
        uid = p["user_id"]
        result.append({
            "user_id": uid,
            "full_name": p["full_name"],
            "date_of_birth": p["date_of_birth"],
            "sessions": sessions_by_user.get(uid, []),
        })

    return result


@router.post("/reset-exam")
async def reset_exam(
    user_id: str,
    subject: str,
    admin_user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    """Reset (delete) a student's exam session so they can retake it."""
    if subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Invalid subject: {subject}")

    result = await db.exam_sessions.delete_one(
        {"user_id": user_id, "subject": subject}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"success": True, "message": f"Reset {subject} for {user_id}"}


@router.get("/stats")
async def get_stats(
    _: dict = Depends(require_admin),
    db=Depends(get_db),
):
    today = datetime.utcnow().date().isoformat()
    total_students = await db.profiles.count_documents({})
    total_sessions = await db.exam_sessions.count_documents({"completed_at": {"$ne": None}})
    today_certs = await db.exam_sessions.count_documents({
        "certificate_id": {"$ne": None},
        "completed_at": {"$regex": f"^{today}"},
    })
    passed = await db.exam_sessions.count_documents({"passed": True})

    return {
        "total_students": total_students,
        "total_completed_sessions": total_sessions,
        "today_certificates": today_certs,
        "total_passed": passed,
    }


@router.post("/make-admin")
async def make_admin(
    target_user_id: str,
    admin_user: dict = Depends(require_admin),
    db=Depends(get_db),
):
    """Grant admin role to a user."""
    existing = await db.user_roles.find_one({"user_id": target_user_id, "role": "admin"})
    if existing:
        return {"message": "Already an admin"}

    await db.user_roles.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": target_user_id,
        "role": "admin",
        "granted_at": datetime.utcnow().isoformat(),
    })
    return {"message": "Admin role granted"}
