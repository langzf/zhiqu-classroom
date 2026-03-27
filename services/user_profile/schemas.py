"""User Profile Schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from shared.schemas import OrmBase


# ── User ──


class UserCreate(OrmBase):
    phone: str
    nickname: str
    role: str = "student"
    avatar_url: Optional[str] = None


class UserUpdate(OrmBase):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None


class UserOut(OrmBase):
    id: UUID
    phone: str
    nickname: str
    role: str
    avatar_url: Optional[str]
    grade: Optional[str]
    school: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── ParentBinding ──


class GuardianBindingCreate(OrmBase):
    guardian_id: UUID
    student_id: UUID
    relation: str = Field(default="parent", description="parent|guardian|other")


class GuardianBindingOut(OrmBase):
    id: UUID
    guardian_id: UUID
    student_id: UUID
    relation: str
    created_at: datetime


# ── Auth ──


class LoginRequest(OrmBase):
    phone: str
    code: str = Field(description="短信验证码")


class TokenOut(OrmBase):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(OrmBase):
    phone: str
    nickname: str
    role: str = "student"
    code: str = Field(description="短信验证码")
