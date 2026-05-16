"""Voice profiles and speech service integration."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse
from uuid import UUID
import re

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.voice import UserVoiceSetting, VoiceProfile
from shared.exceptions import BusinessError, NotFoundError, ValidationError
from shared.logging import report_trace_event

log = structlog.get_logger(__name__)


def _with_default_path(base_url: str, default_path: str) -> str:
    parsed = urlparse(base_url)
    if parsed.path and parsed.path != "/":
        return base_url
    return base_url.rstrip("/") + default_path


def _response_snippet(response: httpx.Response | None, limit: int = 500) -> str:
    if response is None:
        return ""
    try:
        return response.text[:limit]
    except Exception:
        return ""


def _prepare_speech_text(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"[*_`#>\[\]]", "", value)
    value = re.sub(r"\([^()\u4e00-\u9fff]*[\u4e00-\u9fff][^()]*\)", "", value)
    value = re.sub(r"[\U00010000-\U0010ffff]", "", value)
    chinese_count = sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
    if chinese_count:
        lines = []
        for line in re.split(r"[\r\n]+", value):
            ascii_alpha_count = sum(1 for ch in line if ch.isascii() and ch.isalpha())
            line_chinese_count = sum(1 for ch in line if "\u4e00" <= ch <= "\u9fff")
            if line_chinese_count or ascii_alpha_count <= 12:
                lines.append(line)
        value = " ".join(lines).strip() or value
        value = re.sub(r"\b[A-Za-z][A-Za-z0-9' -]{14,}[.!?]?", "", value)
        value = re.sub(r"\b[A-Za-z]{2,}\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:1800] or text


def _has_chinese(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text or "")


def _voice_lang_code(voice: str | None) -> str | None:
    if not voice:
        return None
    prefix = voice.strip()[:1].lower()
    return prefix or None


class VoiceService:
    def __init__(self, db: AsyncSession, settings) -> None:
        self.db = db
        self.settings = settings

    async def list_profiles(self, include_inactive: bool = False) -> list[VoiceProfile]:
        stmt = select(VoiceProfile).where(VoiceProfile.deleted_at.is_(None))
        if not include_inactive:
            stmt = stmt.where(VoiceProfile.is_active.is_(True))
        stmt = stmt.order_by(VoiceProfile.sort_order, VoiceProfile.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_profile(
        self,
        *,
        name: str,
        description: str | None,
        provider: str,
        voice_key: str | None,
        is_active: bool,
        sort_order: int,
        created_by: str | None,
        reference_filename: str | None = None,
        reference_content_type: str | None = None,
        reference_audio: bytes | None = None,
    ) -> VoiceProfile:
        provider = provider or "tts"
        if provider not in ("tts", "openvoice"):
            raise ValidationError("provider must be tts or openvoice")
        if provider == "openvoice" and not reference_audio:
            raise ValidationError("openvoice profile requires reference audio")

        row = VoiceProfile(
            name=name,
            description=description,
            provider=provider,
            voice_key=voice_key or self.settings.default_tts_voice,
            is_active=is_active,
            sort_order=sort_order,
            created_by=created_by,
            reference_filename=reference_filename,
            reference_content_type=reference_content_type,
            reference_audio=reference_audio,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        log.info("voice_profile.created", voice_profile_id=row.id, provider=row.provider)
        return row

    async def get_profile(self, profile_id: UUID | str) -> VoiceProfile:
        row = (
            await self.db.execute(
                select(VoiceProfile).where(
                    VoiceProfile.id == str(profile_id),
                    VoiceProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise NotFoundError("voice_profile", str(profile_id))
        return row

    async def get_user_setting(self, user_id: str) -> tuple[UserVoiceSetting, Optional[VoiceProfile]]:
        setting = (
            await self.db.execute(
                select(UserVoiceSetting).where(UserVoiceSetting.user_id == user_id)
            )
        ).scalar_one_or_none()
        if not setting:
            setting = UserVoiceSetting(user_id=user_id, auto_play=False)
            self.db.add(setting)
            await self.db.flush()
            await self.db.refresh(setting)

        profile = None
        if setting.voice_profile_id:
            profile = await self.get_profile(setting.voice_profile_id)
        return setting, profile

    async def update_user_setting(
        self,
        *,
        user_id: str,
        voice_profile_id: UUID | None,
        auto_play: bool,
    ) -> tuple[UserVoiceSetting, Optional[VoiceProfile]]:
        profile = None
        if voice_profile_id:
            profile = await self.get_profile(voice_profile_id)
            if not profile.is_active:
                raise ValidationError("voice profile is inactive")

        setting = (
            await self.db.execute(
                select(UserVoiceSetting).where(UserVoiceSetting.user_id == user_id)
            )
        ).scalar_one_or_none()
        if not setting:
            setting = UserVoiceSetting(user_id=user_id)
            self.db.add(setting)
        setting.voice_profile_id = str(voice_profile_id) if voice_profile_id else None
        setting.auto_play = auto_play
        await self.db.flush()
        await self.db.refresh(setting)
        return setting, profile

    async def transcribe(self, *, filename: str, content_type: str, audio: bytes) -> str:
        if not audio:
            raise ValidationError("empty audio file")
        files = {"file": (filename or "recording.wav", audio, content_type or "audio/wav")}
        data = {
            "temperature": "0.0",
            "response_format": "json",
        }
        url = _with_default_path(self.settings.stt_service_url, "/inference")
        report_trace_event(
            level="info",
            message="voice_stt_request_start",
            path=urlparse(url).path,
            method="POST",
            meta={
                "voiceService": "stt",
                "filename": filename,
                "contentType": content_type,
                "audioBytes": len(audio),
                "targetHost": urlparse(url).netloc,
            },
        )
        async with httpx.AsyncClient(timeout=90) as client:
            try:
                resp = await client.post(url, data=data, files=files)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log.error(
                    "voice_stt_http_failed",
                    url=url,
                    status_code=exc.response.status_code,
                    response_body=_response_snippet(exc.response),
                    filename=filename,
                    content_type=content_type,
                    audio_bytes=len(audio),
                    exc_info=True,
                )
                report_trace_event(
                    level="error",
                    message="voice_stt_http_failed",
                    path=urlparse(url).path,
                    method="POST",
                    status_code=exc.response.status_code,
                    error=exc,
                    meta={
                        "voiceService": "stt",
                        "targetHost": urlparse(url).netloc,
                        "responseBody": _response_snippet(exc.response),
                        "audioBytes": len(audio),
                    },
                )
                raise BusinessError("voice transcription service failed", status_code=502) from exc
            except httpx.HTTPError as exc:
                log.error(
                    "voice_stt_request_failed",
                    url=url,
                    filename=filename,
                    content_type=content_type,
                    audio_bytes=len(audio),
                    error=str(exc),
                    exc_info=True,
                )
                report_trace_event(
                    level="error",
                    message="voice_stt_request_failed",
                    path=urlparse(url).path,
                    method="POST",
                    error=exc,
                    meta={
                        "voiceService": "stt",
                        "targetHost": urlparse(url).netloc,
                        "audioBytes": len(audio),
                    },
                )
                raise BusinessError("voice transcription service unavailable", status_code=502) from exc

        report_trace_event(
            level="info",
            message="voice_stt_request_success",
            path=urlparse(url).path,
            method="POST",
            status_code=resp.status_code,
            meta={
                "voiceService": "stt",
                "targetHost": urlparse(url).netloc,
                "contentType": resp.headers.get("content-type", ""),
            },
        )
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            data = resp.json()
            for key in ("text", "transcript", "result"):
                if isinstance(data, dict) and data.get(key):
                    return str(data[key])
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                for key in ("text", "transcript", "result"):
                    if data["data"].get(key):
                        return str(data["data"][key])
            return str(data)
        return resp.text.strip()

    async def synthesize(self, *, text: str, profile_id: UUID | str | None = None) -> tuple[bytes, str]:
        profile = await self._resolve_profile(profile_id)
        text = _prepare_speech_text(text)
        if profile.provider == "openvoice":
            return await self._openvoice(text, profile)
        return await self._tts(text, profile)

    async def _resolve_profile(self, profile_id: UUID | str | None) -> VoiceProfile:
        if profile_id:
            return await self.get_profile(profile_id)
        stmt = (
            select(VoiceProfile)
            .where(
                VoiceProfile.is_active.is_(True),
                VoiceProfile.deleted_at.is_(None),
                VoiceProfile.provider == "tts",
            )
            .order_by(VoiceProfile.sort_order, VoiceProfile.created_at.desc())
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalars().first()
        if not row:
            raise NotFoundError("voice_profile")
        return row

    async def _tts(self, text: str, profile: VoiceProfile) -> tuple[bytes, str]:
        is_chinese = _has_chinese(text)
        requested_voice = profile.voice_key or self.settings.default_tts_voice
        voice = requested_voice
        lang_code = _voice_lang_code(voice)
        if is_chinese and lang_code != "z":
            voice = self.settings.default_tts_chinese_voice
            lang_code = "z"
        payload = {
            "model": self.settings.default_tts_model,
            "input": text,
            "voice": voice,
            "lang_code": lang_code,
            "response_format": "mp3",
        }
        url = _with_default_path(self.settings.tts_service_url, "/v1/audio/speech")
        report_trace_event(
            level="info",
            message="voice_tts_request_start",
            path=urlparse(url).path,
            method="POST",
            meta={
                "voiceService": "tts",
                "provider": profile.provider,
                "voiceProfileId": str(profile.id),
                "voiceKey": requested_voice,
                "resolvedVoice": voice,
                "langCode": lang_code,
                "textLanguage": "zh-CN" if is_chinese else "auto",
                "textLength": len(text),
                "targetHost": urlparse(url).netloc,
            },
        )
        async with httpx.AsyncClient(timeout=90) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log.error(
                    "voice_tts_http_failed",
                    url=url,
                    status_code=exc.response.status_code,
                    response_body=_response_snippet(exc.response),
                    profile_id=str(profile.id),
                    requested_voice=requested_voice,
                    resolved_voice=voice,
                    lang_code=lang_code,
                    exc_info=True,
                )
                report_trace_event(
                    level="error",
                    message="voice_tts_http_failed",
                    path=urlparse(url).path,
                    method="POST",
                    status_code=exc.response.status_code,
                    error=exc,
                    meta={
                        "voiceService": "tts",
                        "targetHost": urlparse(url).netloc,
                        "voiceProfileId": str(profile.id),
                        "voiceKey": requested_voice,
                        "resolvedVoice": voice,
                        "langCode": lang_code,
                        "textLanguage": "zh-CN" if is_chinese else "auto",
                        "responseBody": _response_snippet(exc.response),
                    },
                )
                raise BusinessError("speech synthesis service failed", status_code=502) from exc
            except httpx.HTTPError as exc:
                log.error(
                    "voice_tts_request_failed",
                    url=url,
                    profile_id=str(profile.id),
                    requested_voice=requested_voice,
                    resolved_voice=voice,
                    lang_code=lang_code,
                    error=str(exc),
                    exc_info=True,
                )
                report_trace_event(
                    level="error",
                    message="voice_tts_request_failed",
                    path=urlparse(url).path,
                    method="POST",
                    error=exc,
                    meta={
                        "voiceService": "tts",
                        "targetHost": urlparse(url).netloc,
                        "voiceProfileId": str(profile.id),
                        "voiceKey": requested_voice,
                        "resolvedVoice": voice,
                        "langCode": lang_code,
                        "textLanguage": "zh-CN" if is_chinese else "auto",
                    },
                )
                raise BusinessError("speech synthesis service unavailable", status_code=502) from exc
        report_trace_event(
            level="info",
            message="voice_tts_request_success",
            path=urlparse(url).path,
            method="POST",
            status_code=resp.status_code,
            meta={
                "voiceService": "tts",
                "targetHost": urlparse(url).netloc,
                "voiceProfileId": str(profile.id),
                "voiceKey": requested_voice,
                "resolvedVoice": voice,
                "langCode": lang_code,
                "textLanguage": "zh-CN" if is_chinese else "auto",
                "contentType": resp.headers.get("content-type", ""),
                "audioBytes": len(resp.content),
            },
        )
        return resp.content, resp.headers.get("content-type", "audio/mpeg")

    async def _openvoice(self, text: str, profile: VoiceProfile) -> tuple[bytes, str]:
        if not profile.reference_audio:
            raise ValidationError("openvoice profile has no reference audio")
        files = {
            "reference_audio": (
                profile.reference_filename or "reference.wav",
                profile.reference_audio,
                profile.reference_content_type or "audio/wav",
            )
        }
        data = {"text": text}
        url = _with_default_path(self.settings.openvoice_service_url, "/")
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, data=data, files=files)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                report_trace_event(
                    level="error",
                    message="voice_openvoice_http_failed",
                    path=urlparse(url).path,
                    method="POST",
                    status_code=exc.response.status_code,
                    error=exc,
                    meta={
                        "voiceService": "openvoice",
                        "targetHost": urlparse(url).netloc,
                        "voiceProfileId": str(profile.id),
                        "responseBody": _response_snippet(exc.response),
                    },
                )
                raise BusinessError("openvoice synthesis service failed", status_code=502) from exc
            except httpx.HTTPError as exc:
                report_trace_event(
                    level="error",
                    message="voice_openvoice_request_failed",
                    path=urlparse(url).path,
                    method="POST",
                    error=exc,
                    meta={
                        "voiceService": "openvoice",
                        "targetHost": urlparse(url).netloc,
                        "voiceProfileId": str(profile.id),
                    },
                )
                raise BusinessError("openvoice synthesis service unavailable", status_code=502) from exc
        return resp.content, resp.headers.get("content-type", "audio/mpeg")
