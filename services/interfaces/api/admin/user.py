"""Admin 用户管理路由"""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query

from shared.response import ok, paged
from interfaces.schemas.user import AdminUserUpdate, UserOut
from interfaces.api.deps import AdminUser, UserSvc

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-user"])


@router.get("", summary="用户列表（管理员）")
async def list_users(
    svc: UserSvc,
    _admin: AdminUser,
    role: Optional[str] = Query(None, description="按角色筛选"),
    is_active: Optional[bool] = Query(None),
    keyword: Optional[str] = Query(None, description="手机号/昵称模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_users(
        role=role, is_active=is_active, keyword=keyword,
        page=page, page_size=page_size,
    )
    data = [UserOut.model_validate(u).model_dump() for u in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", summary="用户详情（管理员）")
async def get_user(user_id: UUID, svc: UserSvc, _admin: AdminUser):
    user = await svc.admin_get_user(user_id)
    return ok(UserOut.model_validate(user).model_dump())


@router.patch("/{user_id}", summary="更新用户（管理员）")
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    svc: UserSvc,
    _admin: AdminUser,
):
    user = await svc.admin_update_user(user_id, body)
    return ok(UserOut.model_validate(user).model_dump())
