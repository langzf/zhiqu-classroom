"""
共享 Pydantic Schemas & 统一响应格式
───────────────────────────────────
ApiResponse / PagedResponse / OrmBase / IdTimestampSchema
以及工厂函数 ok() / fail() / paged()
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


# ── 统一响应 ──────────────────────────────────────────


class ApiResponse(BaseModel, Generic[T]):
    """统一 JSON 响应包装"""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class PageMeta(BaseModel):
    """分页元信息"""
    page: int
    page_size: int
    total: int
    total_pages: int


class PagedResponse(BaseModel, Generic[T]):
    """分页响应"""
    code: int = 0
    message: str = "ok"
    data: list[T] = []
    meta: PageMeta


# ── 工厂函数 ──────────────────────────────────────────


def ok(data: Any = None, message: str = "ok") -> dict:
    """成功响应"""
    return {"code": 0, "message": message, "data": data}


def fail(message: str = "error", code: int = -1, data: Any = None) -> dict:
    """失败响应"""
    return {"code": code, "message": message, "data": data}


def paged(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "ok",
) -> dict:
    """分页响应"""
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "code": 0,
        "message": message,
        "data": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


# ── ORM 基础 Schema ──────────────────────────────────


class OrmBase(BaseModel):
    """启用 from_attributes 的 Pydantic 基类"""
    model_config = ConfigDict(from_attributes=True)


class IdTimestampSchema(OrmBase):
    """带 id + 时间戳的通用基类"""
    id: UUID
    created_at: datetime
    updated_at: datetime
