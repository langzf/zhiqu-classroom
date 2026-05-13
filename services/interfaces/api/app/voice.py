"""Student voice APIs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response

from interfaces.api.deps import CurrentUser, VoiceSvc
from interfaces.schemas.voice import SpeechRequest, VoiceProfileOut, VoiceSettingOut, VoiceSettingUpdate
from shared.response import ok

router = APIRouter(prefix="/api/v1/app/voice", tags=["app-voice"])


@router.get("/profiles", summary="可选音色列表")
async def list_profiles(svc: VoiceSvc, _user: CurrentUser):
    rows = await svc.list_profiles()
    return ok([VoiceProfileOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.get("/settings", summary="当前用户语音设置")
async def get_settings(user: CurrentUser, svc: VoiceSvc):
    setting, profile = await svc.get_user_setting(user.sub)
    data = VoiceSettingOut(
        voice_profile_id=setting.voice_profile_id,
        auto_play=setting.auto_play,
        voice_profile=VoiceProfileOut.model_validate(profile) if profile else None,
    )
    return ok(data.model_dump(mode="json"))


@router.patch("/settings", summary="更新当前用户语音设置")
async def update_settings(body: VoiceSettingUpdate, user: CurrentUser, svc: VoiceSvc):
    setting, profile = await svc.update_user_setting(
        user_id=user.sub,
        voice_profile_id=body.voice_profile_id,
        auto_play=body.auto_play,
    )
    data = VoiceSettingOut(
        voice_profile_id=setting.voice_profile_id,
        auto_play=setting.auto_play,
        voice_profile=VoiceProfileOut.model_validate(profile) if profile else None,
    )
    return ok(data.model_dump(mode="json"))


@router.post("/stt", summary="语音转文本")
async def transcribe(_user: CurrentUser, svc: VoiceSvc, file: UploadFile = File(...)):
    audio = await file.read()
    text = await svc.transcribe(
        filename=file.filename or "recording.wav",
        content_type=file.content_type or "audio/wav",
        audio=audio,
    )
    return ok({"text": text})


@router.post("/tts", summary="文本转语音")
async def synthesize(body: SpeechRequest, _user: CurrentUser, svc: VoiceSvc):
    audio, content_type = await svc.synthesize(
        text=body.text,
        profile_id=body.voice_profile_id,
    )
    return Response(content=audio, media_type=content_type)
