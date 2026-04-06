"""
user_profile 数据模型
─────────────────────
Schema: users
Tables: users, student_profiles, user_oauth_bindings, guardian_bindings
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid7


# ── users ─────────────────────────────────────────────


class User(Base, TimestampMixin, SoftDeleteMixin):
    """用户表"""

    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_phone_active",
            "phone",
            unique=True,
            postgresql_where="phone IS NOT NULL AND deleted_at IS NULL",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="昵称"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="头像 URL"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="student",
        comment="角色: student|admin|guardian|teacher",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )

    # relationship
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    oauth_bindings: Mapped[list["UserOAuthBinding"]] = relationship(
        back_populates="user", lazy="noload"
    )
    guardian_bindings_as_guardian: Mapped[list["GuardianBinding"]] = relationship(
        back_populates="guardian",
        foreign_keys="GuardianBinding.guardian_id",
        lazy="noload",
    )
    guardian_bindings_as_student: Mapped[list["GuardianBinding"]] = relationship(
        back_populates="student",
        foreign_keys="GuardianBinding.student_id",
        lazy="noload",
    )


# ── student_profiles ──────────────────────────────────


class StudentProfile(Base, TimestampMixin):
    """学生档案 — 与 User 1:1"""

    __tablename__ = "student_profiles"
    __table_args__ = (
        Index("idx_sp_grade", "grade"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    grade: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="年级: grade_1 ~ grade_12"
    )
    school_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="学校名称"
    )
    learning_style: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="学习风格偏好"
    )
    interests: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="兴趣标签"
    )

    user: Mapped["User"] = relationship(back_populates="student_profile")


# ── user_oauth_bindings ───────────────────────────────


class UserOAuthBinding(Base, TimestampMixin):
    """第三方登录绑定"""

    __tablename__ = "user_oauth_bindings"
    __table_args__ = (
        Index("idx_uob_provider", "provider", "provider_user_id", unique=True),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="wechat|feishu|google"
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="第三方平台用户 ID"
    )
    access_token: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="访问令牌"
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="刷新令牌"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="令牌过期时间"
    )

    user: Mapped["User"] = relationship(back_populates="oauth_bindings")


# ── guardian_bindings ─────────────────────────────────


class GuardianBinding(Base, TimestampMixin, SoftDeleteMixin):
    """家长-学生绑定关系"""

    __tablename__ = "guardian_bindings"
    __table_args__ = (
        Index(
            "idx_gb_guardian_student",
            "guardian_id",
            "student_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    guardian_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="家长 user_id",
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="学生 user_id",
    )
    relationship_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="parent",
        comment="关系类型: parent|grandparent|other",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否为主要监护人"
    )

    guardian: Mapped["User"] = relationship(
        back_populates="guardian_bindings_as_guardian",
        foreign_keys=[guardian_id],
    )
    student: Mapped["User"] = relationship(
        back_populates="guardian_bindings_as_student",
        foreign_keys=[student_id],
    )
