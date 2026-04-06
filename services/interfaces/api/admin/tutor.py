"""管理后台 - AI 导师管理路由"""

from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.tutor_service import TutorService
from infrastructure.persistence.database import get_db
from shared.response import ok, paged
from interfaces.schemas.tutor import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    MessageSend,
    FeedbackCreate,
)

router = APIRouter(prefix="/api/v1/admin/tutor", tags=["admin-tutor"])


@router.post("/conversations", summary="创建会话")
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    conv = await svc.create_conversation(
        student_id=data.student_id,
        scene=data.scene,
        title=data.title,
        context=data.context,
    )
    return ok(ConversationOut.model_validate(conv))


@router.get("/conversations", summary="会话列表")
async def list_conversations(
    scene: str | None = None,
    student_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    items, total = await svc.list_conversations(
        scene=scene,
        student_id=student_id,
        page=page,
        page_size=page_size,
    )
    return paged([ConversationOut.model_validate(c) for c in items], total, page, page_size)


@router.get("/conversations/{conv_id}", summary="会话详情")
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    svc = TutorService(db)
    conv = await svc.get_conversation(conv_id)
    return ok(ConversationOut.model_validate(conv))


@router.patch("/conversations/{conv_id}", summary="更新会话")
async def update_conversation(
    conv_id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    conv = await svc.update_conversation(conv_id, **data.model_dump(exclude_unset=True))
    return ok(ConversationOut.model_validate(conv))


@router.delete("/conversations/{conv_id}", summary="删除会话（软删除）")
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    svc = TutorService(db)
    await svc.soft_delete_conversation(conv_id)
    return ok(None)


@router.get("/conversations/{conv_id}/messages", summary="消息列表")
async def list_messages(
    conv_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    items, total = await svc.list_messages(conv_id, page=page, page_size=page_size)
    return paged([MessageOut.model_validate(m) for m in items], total, page, page_size)


@router.post("/conversations/{conv_id}/messages", summary="发送消息并获取 AI 回复")
async def send_message(
    conv_id: str,
    data: MessageSend,
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    user_msg, ai_msg = await svc.send_and_reply(conv_id, data.content)
    return ok({
        "user_message": MessageOut.model_validate(user_msg),
        "ai_message": MessageOut.model_validate(ai_msg),
    })


@router.post("/conversations/{conv_id}/messages/stream", summary="流式发送消息")
async def send_message_stream(
    conv_id: str,
    data: MessageSend,
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    
    async def event_stream() -> AsyncGenerator[str, None]:
        async for chunk in svc.send_and_reply_stream(conv_id, data.content):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/messages/{message_id}/feedback", summary="消息反馈")
async def add_feedback(
    message_id: str,
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = TutorService(db)
    msg = await svc.add_feedback(message_id, data.rating, data.comment)
    return ok(MessageOut.model_validate(msg))
