"""Voice profile and user voice preference models."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid7


class VoiceProfile(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "voice_profiles"
    __table_args__ = (
        Index("idx_voice_profiles_active", "is_active", "sort_order"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid7)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="tts")
    voice_key: Mapped[str] = mapped_column(String(100), nullable=False, default="af_heart")
    reference_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference_content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_audio: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class UserVoiceSetting(Base, TimestampMixin):
    __tablename__ = "user_voice_settings"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    voice_profile_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("voice_profiles.id", ondelete="SET NULL"), nullable=True
    )
    auto_play: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
