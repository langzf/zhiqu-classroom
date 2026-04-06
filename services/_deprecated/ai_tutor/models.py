"""
ai_tutor 数据模型
─────────────────
Schema: tutor
Tables: conversations, messages

对话与消息，支持多场景 AI 辅导。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base_model import Base, SoftDeleteMixin, TimestampMixin, generate_uuid7


# ── 会话 ──────────────────────────────────────────────


class Conversation(Base, TimestampMixin, SoftDeleteMixin):
    """AI 辅导会话"""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conv_student", "student_id", "updated_at"),
        Index("idx_conv_scene", "scene"),
        {"schema": "tutor"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, comment="学生 user_id"
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="会话标题（自动生成或用户修改）"
    )
    scene: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="free_chat",
        comment="场景: free_chat|homework_help|concept_explain|review_guide|error_analysis",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="状态: active|archived",
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="冗余消息计数"
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后一条消息时间"
    )
    context: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="会话上下文: task_id, chapter_id, knowledge_point_ids, difficulty, student_grade, system_prompt_override",
    )

    # relationship
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", lazy="selectin"
    )


# ── 消息 ──────────────────────────────────────────────


class Message(Base, TimestampMixin):
    """单条对话消息"""

    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_msg_conv", "conversation_id", "created_at"),
        {"schema": "tutor"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tutor.conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="角色: user|assistant|system",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息正文（Markdown）"
    )
    token_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="本条消息 token 数"
    )
    model_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="使用的 LLM 模型"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, comment="扩展元数据"
    )

    # relationship
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
