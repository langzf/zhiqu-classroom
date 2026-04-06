"""
SQLAlchemy 基类 & Mixin
──────────────────────
提供 DeclarativeBase、时间戳 mixin、软删除 mixin、uuid7 生成器。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# re-export Vector 以便其他模块不必直接依赖 pgvector
from pgvector.sqlalchemy import Vector  # noqa: F401


def generate_uuid7() -> str:
    """生成 UUID v7 字符串（时间有序）"""
    import uuid_utils  # 延迟导入
    return str(uuid_utils.uuid7())


class Base(DeclarativeBase):
    """所有 ORM 模型的根基类"""
    pass


class TimestampMixin:
    """created_at / updated_at 自动时间戳"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """软删除 — deleted_at 非空表示已删除"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
