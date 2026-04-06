"""
learning_orchestrator 数据模型
──────────────────────────────
Schema: learning
Tables: tasks, task_items, task_progress

学习任务发布 → 学生领取 → 完成进度跟踪
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base_model import Base, SoftDeleteMixin, TimestampMixin, generate_uuid7


# ── 学习任务 ──────────────────────────────────────────


class Task(Base, TimestampMixin, SoftDeleteMixin):
    """学习任务（由管理员/教师创建）"""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_created_by", "created_by"),
        Index("idx_tasks_publish", "publish_at"),
        {"schema": "learning"},
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
    # 学科 & 年级范围
    subject: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="学科"
    )
    grade_range: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="年级范围 grade_{start}-grade_{end}"
    )
    # 时间窗口
    publish_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="定时发布时间"
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="截止时间"
    )
    # 配置
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="任务配置: max_attempts, time_limit_minutes, pass_score 等",
    )

    # relationships
    items: Mapped[list["TaskItem"]] = relationship(
        back_populates="task", lazy="selectin"
    )


# ── 任务子项 ──────────────────────────────────────────


class TaskItem(Base, TimestampMixin):
    """任务包含的学习内容项"""

    __tablename__ = "task_items"
    __table_args__ = (
        Index("idx_task_items_task", "task_id", "sort_order"),
        {"schema": "learning"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("learning.tasks.id", ondelete="CASCADE"),
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
        comment="关联 content.generated_resources.id（可选）",
    )
    knowledge_point_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="关联知识点（可选）",
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

    # relationship
    task: Mapped["Task"] = relationship(back_populates="items")


# ── 学习进度 ──────────────────────────────────────────


class TaskProgress(Base, TimestampMixin):
    """学生完成任务的进度记录"""

    __tablename__ = "task_progress"
    __table_args__ = (
        Index("idx_tp_student_task", "student_id", "task_id", unique=True),
        Index("idx_tp_status", "status"),
        {"schema": "learning"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("learning.tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="学生 user_id"
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
