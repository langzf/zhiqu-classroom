"""
AI Tutor Pydantic schemas
──────────────────────────
会话 & 消息的请求 / 响应数据结构
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field

from interfaces.schemas.base import OrmBase


# ── Conversation ──────────────────────────────────────


class ConversationCreate(BaseModel):
    """创建会话请求"""

    scene: str = Field(
        default="free_chat",
        description="场景: free_chat|homework_help|concept_explain|review_guide|error_analysis",
    )
    title: Optional[str] = Field(None, max_length=200)
    context: Optional[dict] = Field(
        None,
        description="上下文: task_id, chapter_id, knowledge_point_ids, difficulty, student_grade",
    )


class ConversationUpdate(BaseModel):
    """更新会话请求（部分更新）"""

    title: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, description="active|archived")


class ConversationOut(OrmBase):
    """会话响应"""

    id: UUID
    student_id: UUID
    title: Optional[str]
    scene: str
    status: str
    message_count: int
    last_message_at: Optional[datetime]
    context: Optional[dict]
    created_at: datetime
    updated_at: datetime


# ── Message ───────────────────────────────────────────


class MessageSend(BaseModel):
    """发送消息请求"""

    content: str = Field(..., min_length=1, max_length=5000, description="用户消息")


class MessageOut(OrmBase):
    """消息响应"""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    token_count: Optional[int]
    model_name: Optional[str]
    created_at: datetime


# ── Feedback ──────────────────────────────────────────


class FeedbackCreate(BaseModel):
    """消息反馈请求"""

    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = Field(None, max_length=500)
