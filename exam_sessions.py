from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from auth import get_current_user
from models import ExamSessionCreate, ExamSessionUpdate, ExamSessionComplete, ExamSessionOut
from datetime import datetime
import uuid

router = APIRouter(prefix="/exam-sessions", tags=["exam-sessions"])

SUBJECT_ORDER = ["math", "physics", "english", "life-sciences"]
UNLOCK_DEFAULT = 1440  # minutes


def serialize_session(s: dict) -> dict:
    s.pop("_id", None)
    return s


async def get_settings_doc(db):
    s = await db.admin_settings.find_one({})
    if s:
        return s
    # Default settings
    return {
        "unlock_wait_minutes": UNLOCK_DEFAULT,
        "passing_percentage": 70,
        "per_question_minutes": 3,
        "total_duration_minutes": 90,
    }


@router.get("/mine")
async def get_my_sessions(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return all exam sessions for the current user."""
    cursor = db.exam_sessions.find({"user_id": current_user["user_id"]})
    sessions = []
    async for s in cursor:
        sessions.append(serialize_session(s))
    return sessions


@router.post("/", status_code=201)
async def create_session(
    body: ExamSessionCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Start a new exam session for a subject."""
    user_id = current_user["user_id"]

    # Check there's no incomplete session for this subject
    existing = await db.exam_sessions.find_one(
        {"user_id": user_id, "subject": body.subject, "completed_at": None}
    )
    if existing:
        return serialize_session(existing)

    # Check there's no completed session for this subject (no retakes)
    completed = await db.exam_sessions.find_one(
        {"user_id": user_id, "subject": body.subject, "completed_at": {"$ne": None}}
    )
    if completed:
        raise HTTPException(status_code=409, detail="Exam already completed for this subject")

    # Validate unlock order
    settings = await get_settings_doc(db)
    subject_idx = SUBJECT_ORDER.index(body.subject) if body.subject in SUBJECT_ORDER else -1
    if subject_idx > 0:
        prev_subject = SUBJECT_ORDER[subject_idx - 1]
        prev_session = await db.exam_sessions.find_one(
            {"user_id": user_id, "subject": prev_subject, "completed_at": {"$ne": None}}
        )
        if not prev_session:
            raise HTTPException(status_code=403, detail=f"Complete {prev_subject} first")

        # Check unlock timer
        prev_completed_at = datetime.fromisoformat(prev_session["completed_at"])
        unlock_after = settings.get("unlock_wait_minutes", UNLOCK_DEFAULT)
        from datetime import timedelta
        if datetime.utcnow() < prev_completed_at + timedelta(minutes=unlock_after):
            raise HTTPException(status_code=403, detail="Unlock timer not elapsed")

    now = datetime.utcnow().isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "subject": body.subject,
        "score": None,
        "total_marks": 125,
        "passed": None,
        "certificate_id": None,
        "current_question": 0,
        "time_remaining": body.time_remaining,
        "saved_answers": {},
        "answers": None,
        "topic_scores": None,
        "started_at": now,
        "completed_at": None,
        "created_at": now,
    }
    await db.exam_sessions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/{subject}/progress")
async def save_progress(
    subject: str,
    body: ExamSessionUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Periodically save exam progress."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update"}

    result = await db.exam_sessions.find_one_and_update(
        {"user_id": current_user["user_id"], "subject": subject, "completed_at": None},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Active session not found")
    return serialize_session(result)


@router.post("/{subject}/complete")
async def complete_session(
    subject: str,
    body: ExamSessionComplete,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Submit and complete an exam session."""
    now = datetime.utcnow().isoformat()
    updates = {
        "score": body.score,
        "total_marks": body.total_marks,
        "passed": body.passed,
        "answers": body.answers,
        "certificate_id": body.certificate_id,
        "topic_scores": body.topic_scores,
        "saved_answers": None,
        "time_remaining": None,
        "completed_at": now,
    }

    result = await db.exam_sessions.find_one_and_update(
        {"user_id": current_user["user_id"], "subject": subject, "completed_at": None},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Active session not found")
    return serialize_session(result)
