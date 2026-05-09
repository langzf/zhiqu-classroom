"""管理后台 - AI 导师管理路由"""

from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from shared.response import ok, paged
from interfaces.schemas.tutor import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    MessageSend,
    FeedbackCreate,
)
from interfaces.api.deps import AdminUser, TutorSvc

router = APIRouter(prefix="/api/v1/admin/tutor", tags=["admin-tutor"])


@router.post("/conversations", summary="创建会话")
async def create_conversation(
    data: ConversationCreate,
    user: AdminUser,
    svc: TutorSvc,
):
    conv = await svc.create_conversation(
        student_id=user.sub,
        scene=data.scene,
        title=data.title,
        context=data.context,
    )
    return ok(ConversationOut.model_validate(conv))


@router.get("/conversations", summary="会话列表")
async def list_conversations(
    user: AdminUser,
    svc: TutorSvc,
    scene: str | None = None,
    student_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_conversations(
        scene=scene,
        student_id=student_id,
        page=page,
        page_size=page_size,
    )
    return paged([ConversationOut.model_validate(c) for c in items], total, page, page_size)


@router.get("/conversations/{conv_id}", summary="会话详情")
async def get_conversation(conv_id: str, user: AdminUser, svc: TutorSvc):
    conv = await svc.get_conversation(conv_id)
    return ok(ConversationOut.model_validate(conv))


@router.patch("/conversations/{conv_id}", summary="更新会话")
async def update_conversation(
    conv_id: str,
    data: ConversationUpdate,
    user: AdminUser,
    svc: TutorSvc,
):
    conv = await svc.update_conversation(conv_id, **data.model_dump(exclude_unset=True))
    return ok(ConversationOut.model_validate(conv))


@router.delete("/conversations/{conv_id}", summary="删除会话（软删除）")
async def delete_conversation(conv_id: str, user: AdminUser, svc: TutorSvc):
    await svc.soft_delete_conversation(conv_id)
    return ok(None)


@router.get("/conversations/{conv_id}/messages", summary="消息列表")
async def list_messages(
    conv_id: str,
    user: AdminUser,
    svc: TutorSvc,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    items, total = await svc.list_messages(conv_id, page=page, page_size=page_size)
    return paged([MessageOut.model_validate(m) for m in items], total, page, page_size)


@router.post("/conversations/{conv_id}/messages", summary="发送消息（SSE 流式回复）")
async def send_message(
    conv_id: str,
    data: MessageSend,
    user: AdminUser,
    svc: TutorSvc,
):
    """
    发送消息并以 SSE 流式返回 AI 回复。

    前端通过检查 content-type: text/event-stream 判断为流式，
    逐 chunk 解析 data: {"content": "..."} 事件，
    收到 data: [DONE] 后结束。
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in svc.send_and_reply_stream(conv_id, data.content):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages/{message_id}/feedback", summary="消息反馈")
async def add_feedback(
    message_id: str,
    data: FeedbackCreate,
    user: AdminUser,
    svc: TutorSvc,
):
    feedback = await svc.add_feedback(message_id=message_id, data=data)
    return ok(feedback)
