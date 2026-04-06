"""
learning 数据模型（合并 learning_core + learning_orchestrator）
──────────────────────────────────────────────────────────────
Schema: learning
Tables: tasks, task_items, task_progress, learning_tasks, study_sessions, mastery_records
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
    Float,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid7


# ╔══════════════════════════════════════════════════════╗
# ║  learning_orchestrator 模型                          ║
# ╚══════════════════════════════════════════════════════╝


class Task(Base, TimestampMixin, SoftDeleteMixin):
    """学习任务（由管理员/教师创建）"""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_created_by", "created_by"),
        Index("idx_tasks_publish", "publish_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="任务标题"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="任务描述（Markdown）"
    )
    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="homework",
        comment="类型: homework|review|practice|exploration",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        comment="状态: draft|published|archived",
    )
    created_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="创建者 user_id"
    )
    subject: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="学科"
    )
    grade_range: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="年级范围 grade_{start}-grade_{end}"
    )
    publish_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="定时发布时间"
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="截止时间"
    )
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="任务配置: max_attempts, time_limit_minutes, pass_score 等",
    )

    items: Mapped[list["TaskItem"]] = relationship(
        back_populates="task", lazy="selectin"
    )


class TaskItem(Base, TimestampMixin):
    """任务包含的学习内容项"""

    __tablename__ = "task_items"
    __table_args__ = (
        Index("idx_task_items_task", "task_id", "sort_order"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="类型: game|video_script|quiz|reading|ai_chat",
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="关联 content.generated_resources.id",
    )
    knowledge_point_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="关联知识点",
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="子项标题"
    )
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="子项配置"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )

    task: Mapped["Task"] = relationship(back_populates="items")


class TaskProgress(Base, TimestampMixin):
    """学生完成任务的进度记录"""

    __tablename__ = "task_progress"
    __table_args__ = (
        Index("idx_tp_student_task", "student_id", "task_id", unique=True),
        Index("idx_tp_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="学生 user_id"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_started",
        comment="状态: not_started|in_progress|completed",
    )
    score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="得分（0-100）"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )
    item_progress: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="各子项完成情况: { item_id: { status, score, attempts } }",
    )


# ╔══════════════════════════════════════════════════════╗
# ║  learning_core 模型                                  ║
# ╚══════════════════════════════════════════════════════╝


class LearningTask(Base, TimestampMixin, SoftDeleteMixin):
    """自主学习任务（学生创建的练习/复习任务）"""

    __tablename__ = "learning_tasks"
    __table_args__ = (
        Index("idx_lt_student", "student_id"),
        Index("idx_lt_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="学生 user_id"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="任务标题"
    )
    task_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="exercise",
        comment="类型: exercise|reading|review",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="状态: pending|in_progress|completed|expired",
    )
    subject: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="学科"
    )
    knowledge_point_ids: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="关联知识点 ID 列表"
    )
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="任务配置"
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="截止时间"
    )


class StudySession(Base, TimestampMixin):
    """学习会话 — 记录一段连续学习行为"""

    __tablename__ = "study_sessions"
    __table_args__ = (
        Index("idx_ss_student", "student_id"),
        Index("idx_ss_task", "task_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="学生 user_id"
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True, comment="关联任务 ID"
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="学习时长（秒）"
    )
    activity_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="study",
        comment="活动类型: study|quiz|review|ai_chat",
    )
    summary: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="会话摘要数据"
    )


class MasteryRecord(Base, TimestampMixin):
    """知识点掌握度记录"""

    __tablename__ = "mastery_records"
    __table_args__ = (
        Index("idx_mr_student_kp", "student_id", "knowledge_point_id", unique=True),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="学生 user_id"
    )
    knowledge_point_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        comment="知识点 ID"
    )
    mastery_level: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="掌握度 0.0-1.0"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="练习次数"
    )
    correct_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="正确次数"
    )
    last_practiced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="上次练习时间"
    )
    history: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="历史记录"
    )
