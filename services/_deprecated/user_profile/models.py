"""user_profile 数据模型 — 4 张表"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base_model import Base, TimestampMixin, SoftDeleteMixin, generate_uuid7


# ── users ─────────────────────────────────────────────

class User(Base, TimestampMixin, SoftDeleteMixin):
    """用户表 — 所有角色的基础身份"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="手机号，微信登录用户可为空"
    )
    nickname: Mapped[str] = mapped_column(
        String(50), nullable=False, default="", comment="昵称"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="头像 URL"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="student",
        comment="角色: student / guardian / admin",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # relationships
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user", uselist=False, lazy="selectin",
    )
    oauth_bindings: Mapped[list["UserOAuthBinding"]] = relationship(
        back_populates="user", lazy="selectin",
    )

    __table_args__ = (
        # phone 部分唯一索引（仅非空 + 未删除的记录）
        Index(
            "uniq_users_phone",
            "phone",
            unique=True,
            postgresql_where=text("phone IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("idx_users_role", "role"),
    )


# ── student_profiles ──────────────────────────────────

class StudentProfile(Base, TimestampMixin):
    """学生档案 — 与 users 1:1"""
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    grade: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="年级，如 grade_7"
    )
    school_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
    )
    learning_preference: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=None, comment="学习偏好"
    )
    difficulty_preference: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="难度偏好 1-5"
    )

    user: Mapped["User"] = relationship(back_populates="student_profile")


# ── user_oauth_bindings ───────────────────────────────

class UserOAuthBinding(Base, TimestampMixin):
    """OAuth 绑定 — 微信等第三方登录"""
    __tablename__ = "user_oauth_bindings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="wechat_mp / wechat_h5"
    )
    open_id: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    union_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
    )
    access_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="加密存储"
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    raw_profile: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="原始第三方用户信息"
    )

    user: Mapped["User"] = relationship(back_populates="oauth_bindings")

    __table_args__ = (
        UniqueConstraint("provider", "open_id", name="uniq_oauth_provider_openid"),
    )


# ── guardian_bindings ─────────────────────────────────

class GuardianBinding(Base, TimestampMixin):
    """家长-学生绑定关系"""
    __tablename__ = "guardian_bindings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    guardian_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="家长 user_id",
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="学生 user_id",
    )
    relationship_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="other",
        comment="father / mother / grandparent / other",
    )
    bind_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending / active / revoked",
    )

    __table_args__ = (
        UniqueConstraint("guardian_id", "student_id", name="uniq_guardian_student"),
    )
