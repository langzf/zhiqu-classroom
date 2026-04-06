"""App AI 辅导路由 — 会话 / 消息 / 反馈"""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from shared.response import ok, paged
from interfaces.schemas.tutor import (
    ConversationCreate, ConversationUpdate, ConversationOut,
    MessageSend, MessageOut, FeedbackCreate,
)
from interfaces.api.deps import CurrentUser, TutorSvc

router = APIRouter(prefix="/api/v1/app/tutor", tags=["app-tutor"])


# ── 会话 CRUD ─────────────────────────────────────────

@router.post("/conversations", summary="创建会话")
async def create_conversation(
    body: ConversationCreate, user: CurrentUser, svc: TutorSvc,
):
    conv = await svc.create_conversation(
        student_id=user.sub,
        scene=body.scene,
        title=body.title,
        context=body.context,
    )
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.get("/conversations", summary="会话列表")
async def list_conversations(
    user: CurrentUser,
    svc: TutorSvc,
    scene: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_conversations(
        student_id=user.sub, scene=scene,
        page=page, page_size=page_size,
    )
    data = [ConversationOut.model_validate(c).model_dump() for c in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.get("/conversations/{conv_id}", summary="会话详情")
async def get_conversation(conv_id: UUID, user: CurrentUser, svc: TutorSvc):
    conv = await svc.get_conversation(str(conv_id))
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.patch("/conversations/{conv_id}", summary="更新会话")
async def update_conversation(
    conv_id: UUID, body: ConversationUpdate,
    user: CurrentUser, svc: TutorSvc,
):
    conv = await svc.update_conversation(str(conv_id), **body.model_dump(exclude_unset=True))
    return ok(ConversationOut.model_validate(conv).model_dump())


@router.delete("/conversations/{conv_id}", summary="删除会话（软删除）")
async def delete_conversation(conv_id: UUID, user: CurrentUser, svc: TutorSvc):
    await svc.soft_delete_conversation(str(conv_id))
    return ok()


# ── 消息 ──────────────────────────────────────────────

@router.post("/conversations/{conv_id}/messages", summary="发送消息并获取 AI 回复")
async def send_message(
    conv_id: UUID, body: MessageSend,
    user: CurrentUser, svc: TutorSvc,
):
    user_msg, ai_msg = await svc.send_and_reply(
        conversation_id=str(conv_id), content=body.content, role="student",
    )
    return ok({
        "user_message": MessageOut.model_validate(user_msg).model_dump(),
        "ai_message": MessageOut.model_validate(ai_msg).model_dump(),
    })


@router.post("/conversations/{conv_id}/messages/stream", summary="流式发送消息")
async def send_message_stream(
    conv_id: UUID, body: MessageSend,
    user: CurrentUser, svc: TutorSvc,
):
    stream = svc.send_and_reply_stream(
        conversation_id=str(conv_id), content=body.content, role="student",
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get("/conversations/{conv_id}/messages", summary="消息列表")
async def list_messages(
    conv_id: UUID,
    user: CurrentUser,
    svc: TutorSvc,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    items, total = await svc.list_messages(
        conversation_id=str(conv_id), page=page, page_size=page_size,
    )
    data = [MessageOut.model_validate(m).model_dump() for m in items]
    return paged(data, total=total, page=page, page_size=page_size)


# ── 反馈 ──────────────────────────────────────────────

@router.post("/messages/{message_id}/feedback", summary="消息评价")
async def add_feedback(
    message_id: UUID, body: FeedbackCreate,
    user: CurrentUser, svc: TutorSvc,
):
    fb = await svc.add_feedback(message_id=str(message_id), data=body)
    return ok(fb)
