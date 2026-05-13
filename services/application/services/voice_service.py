"""Voice profiles and speech service integration."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.voice import UserVoiceSetting, VoiceProfile
from shared.exceptions import NotFoundError, ValidationError

log = structlog.get_logger(__name__)


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
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(self.settings.stt_service_url, files=files)
            resp.raise_for_status()
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
        if profile.provider == "openvoice":
            return await self._openvoice(text, profile)
        return await self._tts(text, profile)

    async def _resolve_profile(self, profile_id: UUID | str | None) -> VoiceProfile:
        if profile_id:
            return await self.get_profile(profile_id)
        row = (
            await self.db.execute(
                select(VoiceProfile).where(
                    VoiceProfile.is_active.is_(True),
                    VoiceProfile.deleted_at.is_(None),
                    VoiceProfile.provider == "tts",
                ).order_by(VoiceProfile.sort_order, VoiceProfile.created_at.desc())
            )
        ).scalar_one_or_none()
        if not row:
            raise NotFoundError("voice_profile")
        return row

    async def _tts(self, text: str, profile: VoiceProfile) -> tuple[bytes, str]:
        payload = {
            "model": self.settings.default_tts_model,
            "input": text,
            "voice": profile.voice_key or self.settings.default_tts_voice,
        }
        url = self.settings.tts_service_url.rstrip("/") + "/v1/audio/speech"
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
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
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.settings.openvoice_service_url, data=data, files=files)
            resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "audio/mpeg")
