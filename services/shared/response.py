"""统一响应格式 — ApiResponse, PagedResponse, 工厂函数"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


# ── 统一响应 ──────────────────────────────────────────

class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应包装"""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
    request_id: Optional[str] = None


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PagedResponse(BaseModel, Generic[T]):
    """分页响应"""
    code: int = 0
    message: str = "ok"
    data: Optional[list[T]] = None
    meta: Optional[PageMeta] = None
    request_id: Optional[str] = None


# ── 工厂函数 ──────────────────────────────────────────

def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def fail(code: int = -1, message: str = "error", data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}


def paged(items: list, total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "code": 0,
        "message": "ok",
        "data": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }
