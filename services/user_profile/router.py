"""
user-profile 路由
───────────────────
/api/v1/user
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import TokenPayload, get_current_user, require_role
from shared.schemas import ok, paged

from .schemas import (
    AdminUserUpdate,
    GuardianBindingCreate,
    GuardianBindingOut,
    LoginRequest,
    RegisterRequest,
    TokenOut,
    UserOut,
    UserUpdate,
)
from .service import UserService

router = APIRouter(prefix="/api/v1/user", tags=["user-profile"])

# ── Redis（由 main.py lifespan 注入）────────────────

_redis = None


def set_redis(redis_client):
    """接收 Redis 客户端实例（MVP 暂未使用，预留验证码等功能）"""
    global _redis
    _redis = redis_client


def get_redis():
    return _redis


# ── 依赖 ────────────────────────────────────────────

async def _build_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


Svc = Annotated[UserService, Depends(_build_service)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


# ── 注册 / 登录 ─────────────────────────────────────

@router.post("/register")
async def register(body: RegisterRequest, svc: Svc):
    """注册新用户"""
    user = await svc.register(
        phone=body.phone,
        nickname=body.nickname,
        role=body.role,
    )
    return ok(UserOut.model_validate(user).model_dump())


@router.post("/login")
async def login(body: LoginRequest, svc: Svc):
    """手机号登录（MVP 跳过验证码）"""
    result = await svc.login(phone=body.phone)
    user_data = UserOut.model_validate(result["user"]).model_dump()
    return ok({
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "expires_in": result["expires_in"],
        "user": user_data,
    })


@router.post("/refresh")
async def refresh_token(body: dict, svc: Svc):
    """用 refresh_token 换取新的 access_token"""
    rt = body.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=422, detail="refresh_token is required")
    result = await svc.refresh_access_token(rt)
    return ok(result)


# ── 个人信息 ─────────────────────────────────────────

@router.get("/me")
async def get_me(svc: Svc, user: CurrentUser):
    """获取当前用户信息"""
    u = await svc.get_user(str(user.sub))
    return ok(UserOut.model_validate(u).model_dump())


@router.patch("/me")
async def update_me(body: UserUpdate, svc: Svc, user: CurrentUser):
    """更新当前用户信息"""
    u = await svc.update_user(
        str(user.sub),
        **body.model_dump(exclude_none=True),
    )
    return ok(UserOut.model_validate(u).model_dump())


# ── 家长绑定 ─────────────────────────────────────────

@router.post("/guardian-bindings")
async def bind_guardian(body: GuardianBindingCreate, svc: Svc, user: CurrentUser):
    """绑定家长和学生"""
    binding = await svc.bind_guardian(
        guardian_id=str(body.guardian_id),
        student_id=str(body.student_id),
        relation=body.relationship_type,
    )
    return ok(GuardianBindingOut.model_validate(binding).model_dump())


@router.get("/children")
async def list_children(svc: Svc, user: CurrentUser):
    """获取家长绑定的所有学生"""
    children = await svc.list_children(str(user.sub))
    return ok([UserOut.model_validate(c).model_dump() for c in children])


# ── 管理员用户管理 ─────────────────────────────────────

AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]


@router.get("/users")
async def list_users(
    svc: Svc,
    admin: AdminUser,
    role: str | None = None,
    is_active: bool | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """管理员: 分页查询用户列表"""
    offset = (page - 1) * page_size
    users, total = await svc.list_users(
        role=role,
        is_active=is_active,
        keyword=keyword,
        limit=page_size,
        offset=offset,
    )
    return paged(
        items=[UserOut.model_validate(u).model_dump() for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}")
async def get_user(user_id: UUID, svc: Svc, admin: AdminUser):
    """管理员: 获取用户详情"""
    u = await svc.admin_get_user(user_id)
    return ok(UserOut.model_validate(u).model_dump())


@router.patch("/users/{user_id}")
async def update_user(user_id: UUID, body: AdminUserUpdate, svc: Svc, admin: AdminUser):
    """管理员: 更新用户信息"""
    u = await svc.admin_update_user(user_id, **body.model_dump(exclude_none=True))
    return ok(UserOut.model_validate(u).model_dump())
