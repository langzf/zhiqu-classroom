"""Admin voice profile management APIs."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from interfaces.api.deps import AdminUser, VoiceSvc
from interfaces.schemas.voice import SpeechRequest, VoiceProfileOut
from shared.response import ok

router = APIRouter(prefix="/api/v1/admin/voice", tags=["admin-voice"])


@router.get("/profiles", summary="音色列表")
async def list_profiles(svc: VoiceSvc, _admin: AdminUser, include_inactive: bool = True):
    rows = await svc.list_profiles(include_inactive=include_inactive)
    return ok([VoiceProfileOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("/profiles", summary="上传或登记音色")
async def create_profile(
    svc: VoiceSvc,
    admin: AdminUser,
    name: str = Form(...),
    description: str | None = Form(None),
    provider: str = Form("tts"),
    voice_key: str | None = Form(None),
    is_active: bool = Form(True),
    sort_order: int = Form(0),
    file: UploadFile | None = File(None),
):
    audio = await file.read() if file else None
    row = await svc.create_profile(
        name=name,
        description=description,
        provider=provider,
        voice_key=voice_key,
        is_active=is_active,
        sort_order=sort_order,
        created_by=admin.sub,
        reference_filename=file.filename if file else None,
        reference_content_type=file.content_type if file else None,
        reference_audio=audio,
    )
    return ok(VoiceProfileOut.model_validate(row).model_dump(mode="json"))


@router.post("/stt", summary="语音转文本")
async def transcribe(_admin: AdminUser, svc: VoiceSvc, file: UploadFile = File(...)):
    audio = await file.read()
    text = await svc.transcribe(
        filename=file.filename or "recording.wav",
        content_type=file.content_type or "audio/wav",
        audio=audio,
    )
    return ok({"text": text})


@router.post("/tts", summary="文本转语音")
async def synthesize(body: SpeechRequest, _admin: AdminUser, svc: VoiceSvc):
    audio, content_type = await svc.synthesize(
        text=body.text,
        profile_id=body.voice_profile_id,
    )
    return Response(content=audio, media_type=content_type)
