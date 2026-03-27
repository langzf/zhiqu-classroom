"""
ai_tutor 路由
─────────────
路径前缀：/api/v1/tutor
MVP 端点：会话 CRUD + 消息收发 + 消息反馈
"""

from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query

from database import get_db
from deps import get_current_user
from shared.exceptions import ForbiddenError
from shared.schemas import ok, paged
from shared.security import TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from ai_tutor.schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    FeedbackCreate,
    MessageOut,
    MessageSend,
)
from ai_tutor.service import TutorService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/tutor", tags=["ai-tutor"])


# ── 内部依赖 ──────────────────────────────────────────


def _build_service(db: AsyncSession = Depends(get_db)) -> TutorService:
    return TutorService(db=db)


Svc = Annotated[TutorService, Depends(_build_service)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


def _ensure_owner(conv_student_id: str, user: TokenPayload) -> None:
    """确认当前用户是会话所有者（或管理员）"""
    if user.role != "admin" and conv_student_id != user.sub:
        raise ForbiddenError("无权操作此会话")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 会话
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/conversations")
async def create_conversation(body: ConversationCreate, user: CurrentUser, svc: Svc):
    """
    创建 AI 辅导会话
    - student_id 从 JWT 中获取
    - 可指定场景、标题、上下文
    """
    conv = await svc.create_conversation(
        student_id=user.sub,
        scene=body.scene,
        title=body.title,
        context=body.context,
    )
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.get("/conversations")
async def list_conversations(
    user: CurrentUser,
    svc: Svc,
    scene: Optional[str] = Query(None, description="场景过滤"),
    status: str = Query("active", description="状态: active|archived"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """我的会话列表（分页）"""
    items, total = await svc.list_conversations(
        student_id=user.sub,
        scene=scene,
        status=status,
        page=page,
        page_size=page_size,
    )
    return paged(
        items=[ConversationOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user: CurrentUser, svc: Svc):
    """获取会话详情"""
    conv = await svc.get_conversation(conversation_id)
    _ensure_owner(conv.student_id, user)
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str, body: ConversationUpdate, user: CurrentUser, svc: Svc
):
    """更新会话（标题、状态）"""
    conv = await svc.get_conversation(conversation_id)
    _ensure_owner(conv.student_id, user)
    update_data = body.model_dump(exclude_unset=True)
    conv = await svc.update_conversation(conversation_id, **update_data)
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, user: CurrentUser, svc: Svc):
    """归档会话"""
    conv = await svc.get_conversation(conversation_id)
    _ensure_owner(conv.student_id, user)
    conv = await svc.archive_conversation(conversation_id)
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: CurrentUser, svc: Svc):
    """软删除会话"""
    conv = await svc.get_conversation(conversation_id)
    _ensure_owner(conv.student_id, user)
    await svc.soft_delete_conversation(conversation_id)
    return ok({"conversation_id": conversation_id, "deleted": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 消息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    user: CurrentUser,
    svc: Svc,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """获取会话消息列表（分页，时间正序）"""
    conv = await svc.get_conversation(conversation_id)
    _ensure_owner(conv.student_id, user)
    items, total = await svc.list_messages(
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
    )
    return paged(
        items=[MessageOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str, body: MessageSend, user: CurrentUser, svc: Svc
):
    """
    发送消息 → AI 回复
    - 保存用户消息
    - 调用 LLM 生成回复
    - 保存 AI 回复
    - 返回 AI 回复消息
    """
    conv = await svc.get_conversation(conversation_id)
    _ensure_owner(conv.student_id, user)
    user_msg, assistant_msg = await svc.send_message(
        conversation_id=conversation_id,
        content=body.content,
    )
    return ok(
        {
            "user_message": MessageOut.model_validate(user_msg).model_dump(),
            "assistant_message": MessageOut.model_validate(assistant_msg).model_dump(),
        }
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 反馈
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/messages/{message_id}/feedback")
async def submit_feedback(
    message_id: str, body: FeedbackCreate, user: CurrentUser, svc: Svc
):
    """
    对 AI 回复提交反馈（MVP 简化版）
    - 将反馈存入 message.metadata
    """
    msg = await svc.get_message(message_id)
    if msg.role != "assistant":
        from shared.exceptions import ValidationError

        raise ValidationError("只能对 AI 回复提交反馈")

    # 存入 metadata
    feedback_data = {
        "feedback": {
            "rating": body.rating,
            "comment": body.comment,
            "user_id": user.sub,
        }
    }
    if msg.metadata_:
        msg.metadata_.update(feedback_data)
    else:
        msg.metadata_ = feedback_data
    await svc.db.flush()

    logger.info(
        "feedback_submitted",
        message_id=message_id,
        rating=body.rating,
    )
    return ok({"message_id": message_id, "feedback_saved": True})
