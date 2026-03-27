"""user_profile Pydantic schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.schemas import OrmBase


# ── Auth ──────────────────────────────────────────────

class SmsSendRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")


class SmsSendResponse(BaseModel):
    expire_seconds: int = 300


class SmsVerifyRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)


class WxLoginRequest(BaseModel):
    code: str = Field(..., description="微信 login code")
    provider: str = Field(default="wechat_mp", description="wechat_mp / wechat_h5")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────

class UserOut(OrmBase):
    id: UUID
    phone: Optional[str] = None
    nickname: str
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)


# ── Student Profile ───────────────────────────────────

class StudentProfileOut(OrmBase):
    id: UUID
    user_id: str
    grade: Optional[str] = None
    school_name: Optional[str] = None
    learning_preference: Optional[dict] = None
    difficulty_preference: int = 3


class StudentProfileUpdateRequest(BaseModel):
    grade: Optional[str] = None
    school_name: Optional[str] = Field(None, max_length=100)
    difficulty_preference: Optional[int] = Field(None, ge=1, le=5)


# ── Guardian Binding ──────────────────────────────────

class GuardianBindingOut(OrmBase):
    id: UUID
    guardian_id: str
    student_id: str
    relationship_type: str
    bind_status: str
    created_at: datetime


class GuardianBindRequest(BaseModel):
    student_phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="学生手机号")
    relationship_type: str = Field(default="other")
