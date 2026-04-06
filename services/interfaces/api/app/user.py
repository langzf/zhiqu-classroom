"""App 用户路由 — 个人信息 / 家长绑定"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from shared.response import ok
from interfaces.schemas.user import UserUpdate, UserOut, GuardianBindingCreate, GuardianBindingOut
from interfaces.api.deps import CurrentUser, UserSvc

router = APIRouter(prefix="/api/v1/app/user", tags=["app-user"])


@router.get("/me", summary="获取当前用户信息")
async def get_me(user: CurrentUser, svc: UserSvc):
    u = await svc.get_user(user.sub)
    return ok(UserOut.model_validate(u).model_dump())


@router.patch("/me", summary="更新个人信息")
async def update_me(body: UserUpdate, user: CurrentUser, svc: UserSvc):
    u = await svc.update_user(user.sub, body)
    return ok(UserOut.model_validate(u).model_dump())


@router.post("/guardian-bindings", summary="绑定家长")
async def bind_guardian(body: GuardianBindingCreate, user: CurrentUser, svc: UserSvc):
    binding = await svc.bind_guardian(body)
    return ok(GuardianBindingOut.model_validate(binding).model_dump())


@router.get("/children", summary="家长查看绑定的学生")
async def list_children(user: CurrentUser, svc: UserSvc):
    children = await svc.list_children(guardian_id=user.sub)
    data = [UserOut.model_validate(c).model_dump() for c in children]
    return ok(data)
