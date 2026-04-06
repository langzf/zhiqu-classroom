"""Admin API — 模型配置管理路由"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from application.services.model_config_service import ModelConfigService
from interfaces.api.deps import AdminUser, AppSettings, DbSession
from interfaces.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigDetail,
    ModelConfigOut,
    ModelConfigUpdate,
    ModelProviderCreate,
    ModelProviderDetail,
    ModelProviderOut,
    ModelProviderUpdate,
    SceneModelBindingCreate,
    SceneModelBindingOut,
    SceneModelBindingUpdate,
)
from shared.response import ok, paged

router = APIRouter(
    prefix="/api/v1/admin/model-config",
    tags=["admin-model-config"],
)


def _svc(db, settings) -> ModelConfigService:
    return ModelConfigService(db=db, settings=settings)


# ═══════════════════════════════════════════════════════════════
#  Provider
# ═══════════════════════════════════════════════════════════════


@router.get("/providers", summary="供应商列表")
async def list_providers(
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    svc = _svc(db, settings)
    rows, total = await svc.list_providers(page=page, size=size, is_active=is_active)
    items = [ModelProviderOut.model_validate(r).model_dump() for r in rows]
    return paged(items=items, total=total, page=page, page_size=size)


@router.get("/providers/{provider_id}", summary="供应商详情")
async def get_provider(
    provider_id: UUID,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.get_provider(provider_id)
    return ok(ModelProviderDetail.model_validate(row).model_dump())


@router.post("/providers", summary="新建供应商", status_code=201)
async def create_provider(
    body: ModelProviderCreate,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.create_provider(body)
    await db.commit()
    return ok(ModelProviderOut.model_validate(row).model_dump())


@router.put("/providers/{provider_id}", summary="更新供应商")
async def update_provider(
    provider_id: UUID,
    body: ModelProviderUpdate,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.update_provider(provider_id, body)
    await db.commit()
    return ok(ModelProviderOut.model_validate(row).model_dump())


@router.delete("/providers/{provider_id}", summary="删除供应商")
async def delete_provider(
    provider_id: UUID,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    await svc.delete_provider(provider_id)
    await db.commit()
    return ok()


@router.post("/providers/{provider_id}/test", summary="测试供应商连接")
async def test_provider(
    provider_id: UUID,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    result = await svc.test_provider_connection(provider_id)
    return ok(result)


# ═══════════════════════════════════════════════════════════════
#  Model Config
# ═══════════════════════════════════════════════════════════════


@router.get("/configs", summary="模型配置列表")
async def list_configs(
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    provider_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
):
    svc = _svc(db, settings)
    rows, total = await svc.list_model_configs(
        page=page, size=size, provider_id=provider_id, is_active=is_active
    )
    items = [ModelConfigOut.model_validate(r).model_dump() for r in rows]
    return paged(items=items, total=total, page=page, page_size=size)


@router.get("/configs/{config_id}", summary="模型配置详情")
async def get_config(
    config_id: UUID,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.get_model_config(config_id)
    return ok(ModelConfigDetail.model_validate(row).model_dump())


@router.post("/configs", summary="新建模型配置", status_code=201)
async def create_config(
    body: ModelConfigCreate,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.create_model_config(body)
    await db.commit()
    return ok(ModelConfigOut.model_validate(row).model_dump())


@router.put("/configs/{config_id}", summary="更新模型配置")
async def update_config(
    config_id: UUID,
    body: ModelConfigUpdate,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.update_model_config(config_id, body)
    await db.commit()
    return ok(ModelConfigOut.model_validate(row).model_dump())


@router.delete("/configs/{config_id}", summary="删除模型配置")
async def delete_config(
    config_id: UUID,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    await svc.delete_model_config(config_id)
    await db.commit()
    return ok()


# ═══════════════════════════════════════════════════════════════
#  Scene Binding
# ═══════════════════════════════════════════════════════════════


@router.get("/bindings", summary="场景绑定列表")
async def list_bindings(
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    svc = _svc(db, settings)
    rows, total = await svc.list_bindings(page=page, size=size)
    items = [SceneModelBindingOut.model_validate(r).model_dump() for r in rows]
    return paged(items=items, total=total, page=page, page_size=size)


@router.post("/bindings", summary="新建场景绑定", status_code=201)
async def create_binding(
    body: SceneModelBindingCreate,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.create_binding(body)
    await db.commit()
    return ok(SceneModelBindingOut.model_validate(row).model_dump())


@router.put("/bindings/{scene_key}", summary="更新场景绑定")
async def update_binding(
    scene_key: str,
    body: SceneModelBindingUpdate,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    row = await svc.update_binding(scene_key, body)
    await db.commit()
    return ok(SceneModelBindingOut.model_validate(row).model_dump())


@router.delete("/bindings/{scene_key}", summary="删除场景绑定")
async def delete_binding(
    scene_key: str,
    db: DbSession,
    settings: AppSettings,
    _user: AdminUser,
):
    svc = _svc(db, settings)
    await svc.delete_binding(scene_key)
    await db.commit()
    return ok()
