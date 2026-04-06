"""Auth 路由 — 公共登录 / 注册 / Token 刷新"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from shared.response import ok
from interfaces.schemas.user import LoginRequest, TokenOut, RegisterRequest
from interfaces.api.deps import UserSvc

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", summary="学生端登录（手机号，不存在自动注册）")
async def login(body: LoginRequest, svc: UserSvc):
    tokens = await svc.login(phone=body.phone, require_admin=False)
    return ok(TokenOut(**tokens).model_dump())


@router.post("/login/admin", summary="管理后台登录")
async def login_admin(body: LoginRequest, svc: UserSvc):
    tokens = await svc.login(phone=body.phone, require_admin=True)
    return ok(TokenOut(**tokens).model_dump())


@router.post("/register", summary="手机号注册")
async def register(body: RegisterRequest, svc: UserSvc):
    user = await svc.register(
        phone=body.phone,
        nickname=body.nickname,
        role=body.role if hasattr(body, "role") else "student",
    )
    return ok({"user_id": str(user.id), "phone": user.phone, "nickname": user.nickname})


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", summary="刷新 Access Token")
async def refresh_token(body: RefreshRequest, svc: UserSvc):
    tokens = await svc.refresh_access_token(body.refresh_token)
    return ok(TokenOut(**tokens).model_dump())
