from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from auth import get_current_user, require_admin
from models import VoucherCreate, VoucherOut, CertificateVerifyOut
from datetime import datetime
import uuid

vouchers_router = APIRouter(prefix="/vouchers", tags=["vouchers"])
certs_router = APIRouter(prefix="/certificates", tags=["certificates"])


# ── Vouchers ──────────────────────────────────────────────────────────────────

@vouchers_router.get("/mine")
async def get_my_vouchers(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    cursor = db.voucher_codes.find({"assigned_to": current_user["user_id"]})
    vouchers = []
    async for v in cursor:
        v.pop("_id", None)
        vouchers.append(v)
    return vouchers


@vouchers_router.post("/", status_code=201, dependencies=[Depends(require_admin)])
async def create_voucher(body: VoucherCreate, db=Depends(get_db)):
    existing = await db.voucher_codes.find_one({"code": body.code})
    if existing:
        raise HTTPException(status_code=409, detail="Voucher code already exists")

    now = datetime.utcnow().isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "code": body.code,
        "value": body.value,
        "type": body.type,
        "subject": body.subject,
        "assigned_to": body.assigned_to,
        "redeemed": False,
        "created_at": now,
        "assigned_at": now if body.assigned_to else None,
    }
    await db.voucher_codes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@vouchers_router.post("/{voucher_id}/assign", dependencies=[Depends(require_admin)])
async def assign_voucher(voucher_id: str, user_id: str, db=Depends(get_db)):
    result = await db.voucher_codes.find_one_and_update(
        {"id": voucher_id, "assigned_to": None},
        {"$set": {"assigned_to": user_id, "assigned_at": datetime.utcnow().isoformat()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Voucher not found or already assigned")
    result.pop("_id", None)
    return result


# ── Certificates ──────────────────────────────────────────────────────────────

@certs_router.get("/verify/{cert_id}", response_model=CertificateVerifyOut)
async def verify_certificate(cert_id: str, db=Depends(get_db)):
    session = await db.exam_sessions.find_one({"certificate_id": cert_id})
    if not session:
        raise HTTPException(status_code=404, detail="Certificate not found")

    profile = await db.profiles.find_one({"user_id": session["user_id"]})
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    return CertificateVerifyOut(
        certificate_id=cert_id,
        student_name=profile["full_name"],
        date_of_birth=profile["date_of_birth"],
        subject=session["subject"],
        score=session["score"],
        total_marks=session["total_marks"],
        topic_scores=session.get("topic_scores", {}),
        completed_at=session["completed_at"],
    )
