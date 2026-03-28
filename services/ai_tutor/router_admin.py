"""AI 辅导 — Admin 路由

前缀: /api/v1/admin/tutor
管理员可查看所有会话、发送测试消息。
"""

from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query

from database import get_db
from deps import get_current_user, require_role
from shared.schemas import ok, paged
from shared.security import TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from ai_tutor.schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    MessageSend,
)
from ai_tutor.service import TutorService

logger = structlog.get_logger()

router = APIRouter(prefix="/tutor", tags=["admin-tutor"])


# ── 内部依赖 ──────────────────────────────────────────

def _build_service(db: AsyncSession = Depends(get_db)) -> TutorService:
    return TutorService(db=db)

Svc = Annotated[TutorService, Depends(_build_service)]
AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 会话管理 — 管理员可查看/管理所有会话
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/conversations")
async def create_conversation(body: ConversationCreate, user: AdminUser, svc: Svc):
    """管理员创建测试会话（以自身 id 为 student_id）"""
    conv = await svc.create_conversation(
        student_id=user.sub,
        scene=body.scene,
        title=body.title,
        context=body.context,
    )
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.get("/conversations")
async def list_conversations(
    user: AdminUser,
    svc: Svc,
    scene: Optional[str] = Query(None),
    status: str = Query("active"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """管理员查看所有会话（不限 student_id）"""
    items, total = await svc.list_conversations(
        student_id=None,  # 管理员看全部
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
async def get_conversation(conversation_id: str, user: AdminUser, svc: Svc):
    conv = await svc.get_conversation(conversation_id)
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str, body: ConversationUpdate, user: AdminUser, svc: Svc
):
    update_data = body.model_dump(exclude_unset=True)
    conv = await svc.update_conversation(conversation_id, **update_data)
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: AdminUser, svc: Svc):
    await svc.soft_delete_conversation(conversation_id)
    return ok({"conversation_id": conversation_id, "deleted": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 消息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    user: AdminUser,
    svc: Svc,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
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
    conversation_id: str, body: MessageSend, user: AdminUser, svc: Svc
):
    """管理员发送测试消息"""
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
