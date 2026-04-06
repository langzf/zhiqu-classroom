"""
User Profile Pydantic schemas
──────────────────────────────
用户、家长绑定、认证
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from interfaces.schemas.base import OrmBase


# ── User ──────────────────────────────────────────────


class UserCreate(OrmBase):
    phone: str
    nickname: str
    role: str = "student"
    avatar_url: Optional[str] = None


class UserUpdate(OrmBase):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class AdminUserUpdate(OrmBase):
    """管理员更新用户信息"""

    nickname: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(OrmBase):
    id: UUID
    phone: Optional[str]
    nickname: str
    role: str
    avatar_url: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def flatten_student_profile(cls, data):
        """Flatten grade/school from nested student_profile relationship."""
        if hasattr(data, "student_profile") and data.student_profile:
            sp = data.student_profile
            d = {
                "id": data.id,
                "phone": data.phone,
                "nickname": data.nickname,
                "role": data.role,
                "avatar_url": data.avatar_url,
                "is_active": data.is_active,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "grade": getattr(sp, "grade", None),
                "school": getattr(sp, "school_name", None),
            }
            return d
        elif hasattr(data, "__dict__"):
            return data
        return data


# ── Guardian Binding ──────────────────────────────────


class GuardianBindingCreate(OrmBase):
    guardian_id: UUID
    student_id: UUID
    relationship_type: str = Field(
        default="parent",
        description="father|mother|grandparent|other",
    )


class GuardianBindingOut(OrmBase):
    id: UUID
    guardian_id: UUID
    student_id: UUID
    relationship_type: str
    bind_status: str
    created_at: datetime


# ── Auth ──────────────────────────────────────────────


class LoginRequest(OrmBase):
    phone: str
    code: Optional[str] = Field(
        default=None, description="SMS code (MVP: optional, skipped)"
    )


class TokenOut(OrmBase):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(OrmBase):
    phone: str
    nickname: str
    role: str = "student"
    code: Optional[str] = Field(
        default=None, description="SMS code (MVP: optional, skipped)"
    )
