"""
learning_core 数据模型
─────────────────────
Schema: learning
Tables: learning_tasks, mastery_records, study_sessions

学习任务分配与进度追踪。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import Base, SoftDeleteMixin, TimestampMixin, generate_uuid7


# ── 学习任务 ──────────────────────────────────────────


class LearningTask(Base, TimestampMixin, SoftDeleteMixin):
    """学习任务（关联知识点，学生可领取并完成）"""

    __tablename__ = "learning_tasks"
    __table_args__ = (
        Index("idx_task_student", "student_id", "status"),
        Index("idx_task_kp", "knowledge_point_id"),
        {"schema": "learning"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="学生 user_id"
    )
    knowledge_point_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="关联知识点 ID"
    )
    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="exercise",
        comment="任务类型: exercise|reading|review",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态: pending|in_progress|completed|expired",
    )
    source_resource_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="关联生成资源 ID（如练习题）",
    )
    score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="完成得分 (0-100)"
    )
    answer_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="答题快照"
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="截止时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )


# ── 掌握度记录 ──────────────────────────────────────────


class MasteryRecord(Base, TimestampMixin):
    """学生对某知识点的掌握度（每人每知识点一条）"""

    __tablename__ = "mastery_records"
    __table_args__ = (
        Index("idx_mastery_student_kp", "student_id", "knowledge_point_id", unique=True),
        {"schema": "learning"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="学生 user_id"
    )
    knowledge_point_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="知识点 ID"
    )
    mastery_level: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="掌握度 0.0-1.0"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="尝试次数"
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近尝试时间"
    )


# ── 学习会话 ──────────────────────────────────────────


class StudySession(Base, TimestampMixin):
    """学习会话（一次连续学习活动的记录）"""

    __tablename__ = "study_sessions"
    __table_args__ = (
        Index("idx_study_student", "student_id", "created_at"),
        {"schema": "learning"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="学生 user_id"
    )
    knowledge_point_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True, comment="关联知识点 ID"
    )
    session_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="exercise",
        comment="会话类型: exercise|reading|tutor_chat",
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="持续时间（秒）"
    )
    events: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="学习事件日志"
    )
