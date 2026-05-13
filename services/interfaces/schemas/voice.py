"""Voice service schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from interfaces.schemas.base import OrmBase


class VoiceProfileOut(OrmBase):
    id: UUID
    name: str
    description: Optional[str] = None
    provider: str
    voice_key: str
    has_reference_audio: bool = False
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def add_reference_flag(cls, data):
        if hasattr(data, "__dict__"):
            d = dict(data.__dict__)
            d["has_reference_audio"] = bool(getattr(data, "reference_audio", None))
            return d
        return data


class VoiceSettingOut(OrmBase):
    voice_profile_id: Optional[UUID] = None
    auto_play: bool = False
    voice_profile: Optional[VoiceProfileOut] = None


class VoiceSettingUpdate(BaseModel):
    voice_profile_id: Optional[UUID] = None
    auto_play: bool = False


class SpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_profile_id: Optional[UUID] = None
