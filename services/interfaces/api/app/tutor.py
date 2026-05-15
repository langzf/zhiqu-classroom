"""App AI 辅导路由 — 会话 / 消息 / 反馈"""

from __future__ import annotations

from pathlib import PurePath
from uuid import UUID
from typing import Optional

import structlog
from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response, StreamingResponse

from infrastructure.external.minio_client import download_file, upload_file
from infrastructure.persistence.models import Message
from shared.response import ok, paged
from shared.exceptions import BusinessError, ForbiddenError, NotFoundError, ValidationError
from shared.logging import report_trace_event
from interfaces.schemas.tutor import (
    ConversationCreate, ConversationUpdate, ConversationOut,
    MessageSend, MessageOut, FeedbackCreate,
)
from interfaces.api.deps import CurrentUser, TutorSvc, VoiceSvc

router = APIRouter(prefix="/api/v1/app/tutor", tags=["app-tutor"])
log = structlog.get_logger(__name__)


def _message_out(message: Message) -> dict:
    return MessageOut.model_validate(message).model_dump(mode="json")


def _audio_url(message_id: str) -> str:
    return f"/app/tutor/messages/{message_id}/audio"


def _audio_extension(filename: str | None, content_type: str | None) -> str:
    suffix = PurePath(filename or "").suffix.lower()
    if suffix in {".mp3", ".m4a", ".wav", ".webm", ".ogg", ".aac"}:
        return suffix
    if content_type == "audio/mpeg":
        return ".mp3"
    if content_type == "audio/mp4":
        return ".m4a"
    if content_type == "audio/webm":
        return ".webm"
    if content_type == "audio/wav":
        return ".wav"
    return ".mp3"


async def _cache_assistant_tts(message: Message, user_id: str, voice_svc: VoiceSvc) -> None:
    setting, _profile = await voice_svc.get_user_setting(user_id)
    if not setting.auto_play:
        message.metadata_ = {**(message.metadata_ or {}), "tts_status": "skipped"}
        return

    try:
        audio, content_type = await voice_svc.synthesize(
            text=message.content,
            profile_id=setting.voice_profile_id,
        )
        object_name = f"tutor/messages/{message.id}/assistant-tts{_audio_extension(None, content_type)}"
        await upload_file(object_name, audio, content_type)
        message.metadata_ = {
            **(message.metadata_ or {}),
            "message_type": "text",
            "tts_status": "ready",
            "audio": {
                "source": "assistant_tts",
                "object_name": object_name,
                "content_type": content_type,
                "url": _audio_url(str(message.id)),
            },
        }
    except Exception as exc:
        message.metadata_ = {**(message.metadata_ or {}), "tts_status": "failed"}
        log.error(
            "assistant_tts_cache_failed",
            message_id=str(message.id),
            user_id=user_id,
            error=str(exc),
            exc_info=True,
        )
        report_trace_event(
            level="error",
            message="assistant_tts_cache_failed",
            path="/api/v1/app/tutor/conversations/{conv_id}/messages/sync",
            method="POST",
            error=exc,
            meta={
                "messageId": str(message.id),
                "userId": user_id,
                "ttsStatus": "failed",
            },
        )


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

@router.post("/conversations/{conv_id}/messages", summary="发送消息（SSE 流式）")
async def send_message(
    conv_id: UUID, body: MessageSend,
    user: CurrentUser, svc: TutorSvc,
):
    stream = svc.send_and_reply_stream(
        conversation_id=str(conv_id), content=body.content, role="student",
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/conversations/{conv_id}/messages/sync", summary="发送文本消息并可预生成语音")
async def send_message_sync(
    conv_id: UUID, body: MessageSend,
    user: CurrentUser, svc: TutorSvc, voice_svc: VoiceSvc,
):
    user_msg, assistant_msg = await svc.send_and_reply(
        conversation_id=str(conv_id),
        content=body.content,
        role="student",
        user_metadata={"message_type": "text"},
    )
    await _cache_assistant_tts(assistant_msg, user.sub, voice_svc)
    return ok({
        "user_message": _message_out(user_msg),
        "assistant_message": _message_out(assistant_msg),
    })


@router.post("/conversations/{conv_id}/voice-messages", summary="发送语音消息")
async def send_voice_message(
    conv_id: UUID,
    user: CurrentUser,
    svc: TutorSvc,
    voice_svc: VoiceSvc,
    file: UploadFile = File(...),
):
    audio = await file.read()
    if not audio:
        raise ValidationError("empty audio file")

    content_type = file.content_type or "audio/mpeg"
    filename = file.filename or "recording.mp3"
    report_trace_event(
        level="info",
        message="voice_message_upload_received",
        path=f"/api/v1/app/tutor/conversations/{conv_id}/voice-messages",
        method="POST",
        meta={
            "conversationId": str(conv_id),
            "userId": user.sub,
            "filename": filename,
            "contentType": content_type,
            "audioBytes": len(audio),
        },
    )
    object_name = (
        f"tutor/conversations/{conv_id}/voice-input/"
        f"{PurePath(filename).stem}-{len(audio)}"
        f"{_audio_extension(filename, content_type)}"
    )
    try:
        await upload_file(object_name, audio, content_type)
    except Exception as exc:
        log.error(
            "voice_message_audio_upload_failed",
            conversation_id=str(conv_id),
            user_id=user.sub,
            object_name=object_name,
            content_type=content_type,
            audio_bytes=len(audio),
            error=str(exc),
            exc_info=True,
        )
        report_trace_event(
            level="error",
            message="voice_message_audio_upload_failed",
            path=f"/api/v1/app/tutor/conversations/{conv_id}/voice-messages",
            method="POST",
            error=exc,
            meta={
                "conversationId": str(conv_id),
                "userId": user.sub,
                "objectName": object_name,
                "contentType": content_type,
                "audioBytes": len(audio),
            },
        )
        raise BusinessError("voice audio storage failed", status_code=502) from exc

    transcript = await voice_svc.transcribe(
        filename=filename,
        content_type=content_type,
        audio=audio,
    )
    transcript = (transcript or "").strip()
    if not transcript:
        report_trace_event(
            level="warn",
            message="voice_message_transcript_empty",
            path=f"/api/v1/app/tutor/conversations/{conv_id}/voice-messages",
            method="POST",
            status_code=422,
            meta={
                "conversationId": str(conv_id),
                "userId": user.sub,
                "objectName": object_name,
                "audioBytes": len(audio),
            },
        )
        raise ValidationError("voice transcript is empty")

    user_metadata = {
        "message_type": "voice",
        "transcript": transcript,
        "audio": {
            "source": "user_upload",
            "object_name": object_name,
            "content_type": content_type,
            "filename": filename,
        },
    }
    report_trace_event(
        level="info",
        message="voice_message_transcript_ready",
        path=f"/api/v1/app/tutor/conversations/{conv_id}/voice-messages",
        method="POST",
        meta={
            "conversationId": str(conv_id),
            "userId": user.sub,
            "objectName": object_name,
            "transcriptLength": len(transcript),
        },
    )
    user_msg, assistant_msg = await svc.send_and_reply(
        conversation_id=str(conv_id),
        content=transcript,
        role="student",
        user_metadata=user_metadata,
    )
    user_metadata["audio"]["url"] = _audio_url(str(user_msg.id))
    user_msg.metadata_ = user_metadata
    await _cache_assistant_tts(assistant_msg, user.sub, voice_svc)

    return ok({
        "user_message": _message_out(user_msg),
        "assistant_message": _message_out(assistant_msg),
    })


@router.get("/messages/{message_id}/audio", summary="下载消息音频")
async def get_message_audio(message_id: UUID, user: CurrentUser, svc: TutorSvc):
    msg = await svc.get_message(str(message_id))
    conv = await svc.get_conversation(str(msg.conversation_id))
    if str(conv.student_id) != user.sub:
        raise ForbiddenError("message audio is not accessible")

    metadata = msg.metadata_ or {}
    audio_meta = metadata.get("audio") if isinstance(metadata, dict) else None
    if not isinstance(audio_meta, dict) or not audio_meta.get("object_name"):
        raise ValidationError("message has no audio")

    try:
        audio = await download_file(audio_meta["object_name"])
    except Exception as exc:
        log.error(
            "message_audio_download_failed",
            message_id=str(message_id),
            user_id=user.sub,
            object_name=audio_meta.get("object_name"),
            error=str(exc),
            exc_info=True,
        )
        report_trace_event(
            level="error",
            message="message_audio_download_failed",
            path=f"/api/v1/app/tutor/messages/{message_id}/audio",
            method="GET",
            error=exc,
            meta={
                "messageId": str(message_id),
                "userId": user.sub,
                "objectName": audio_meta.get("object_name"),
                "audioSource": audio_meta.get("source"),
            },
        )
        raise NotFoundError("message_audio", str(message_id)) from exc
    return Response(content=audio, media_type=audio_meta.get("content_type") or "audio/mpeg")


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
