"""SQLAlchemy 基类 — UUID v7 主键、时间戳、软删除"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid6 import uuid7
from pgvector.sqlalchemy import Vector  # noqa: F401 (re-export for convenience)

import uuid as _uuid


def generate_uuid7() -> _uuid.UUID:
    return uuid7()


class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


class TimestampMixin:
    """created_at + updated_at（UTC）"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """软删除：deleted_at IS NULL 表示未删除"""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)
