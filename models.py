from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime
from enum import Enum


class AppRole(str, Enum):
    admin = "admin"
    user = "user"


class Subject(str, Enum):
    math = "math"
    physics = "physics"
    english = "english"
    life_sciences = "life-sciences"


# ── Auth ──────────────────────────────────────────────────────────────────────
class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


# ── Profile ───────────────────────────────────────────────────────────────────
class ProfileCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileOut(BaseModel):
    user_id: str
    full_name: str
    date_of_birth: str
    avatar_url: Optional[str] = None
    created_at: str


# ── Exam Session ──────────────────────────────────────────────────────────────
class ExamSessionCreate(BaseModel):
    subject: str
    time_remaining: int


class ExamSessionUpdate(BaseModel):
    current_question: Optional[int] = None
    time_remaining: Optional[int] = None
    saved_answers: Optional[Dict[str, str]] = None


class ExamSessionComplete(BaseModel):
    score: int
    total_marks: int
    passed: bool
    answers: List[Dict[str, Any]]
    certificate_id: Optional[str] = None
    topic_scores: Dict[str, Any]


class ExamSessionOut(BaseModel):
    id: str
    user_id: str
    subject: str
    score: Optional[int] = None
    total_marks: int
    passed: Optional[bool] = None
    certificate_id: Optional[str] = None
    current_question: int
    time_remaining: Optional[int] = None
    saved_answers: Optional[Dict[str, str]] = None
    answers: Optional[List[Dict]] = None
    topic_scores: Optional[Dict[str, Any]] = None
    started_at: str
    completed_at: Optional[str] = None
    created_at: str


# ── Admin Settings ─────────────────────────────────────────────────────────────
class AdminSettingsUpdate(BaseModel):
    unlock_wait_minutes: Optional[int] = None
    passing_percentage: Optional[int] = None
    per_question_minutes: Optional[int] = None
    total_duration_minutes: Optional[int] = None


class AdminSettingsOut(BaseModel):
    id: str
    unlock_wait_minutes: int
    passing_percentage: int
    per_question_minutes: int
    total_duration_minutes: int


# ── Voucher ────────────────────────────────────────────────────────────────────
class VoucherCreate(BaseModel):
    code: str
    value: int
    type: str = "airtime"
    subject: Optional[str] = None
    assigned_to: Optional[str] = None


class VoucherOut(BaseModel):
    id: str
    code: str
    value: int
    type: str
    subject: Optional[str] = None
    assigned_to: Optional[str] = None
    redeemed: bool
    created_at: str


# ── Certificate Verify ─────────────────────────────────────────────────────────
class CertificateVerifyOut(BaseModel):
    certificate_id: str
    student_name: str
    date_of_birth: str
    subject: str
    score: int
    total_marks: int
    topic_scores: Dict[str, Any]
    completed_at: str


# ── Admin Student View ─────────────────────────────────────────────────────────
class AdminStudentRow(BaseModel):
    user_id: str
    full_name: str
    date_of_birth: str
    sessions: List[Dict[str, Any]]
