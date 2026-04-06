"""模型配置 Service — Provider / Config / Binding CRUD + 场景解析"""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.persistence.models.model_config import (
    ModelConfig,
    ModelProvider,
    SceneModelBinding,
)
from interfaces.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelProviderCreate,
    ModelProviderUpdate,
    ResolvedModel,
    SceneModelBindingCreate,
    SceneModelBindingUpdate,
)
from shared.crypto import decrypt_api_key, encrypt_api_key
from shared.exceptions import BusinessError, ConflictError, NotFoundError

log = structlog.get_logger(__name__)

# ── 内存缓存 (TTL 5 min) ────────────────────────────────────
_resolve_cache: dict[str, tuple[float, ResolvedModel]] = {}
_CACHE_TTL = 300.0


def _mask_key(raw: str) -> str:
    """API Key 掩码：保留前 4 后 4，中间用 * 代替"""
    if len(raw) <= 8:
        return "****"
    return f"{raw[:4]}{'*' * (len(raw) - 8)}{raw[-4:]}"


def _invalidate_cache(scene_key: str) -> None:
    _resolve_cache.pop(scene_key, None)


class ModelConfigService:
    """模型配置服务"""

    def __init__(self, db: AsyncSession, settings) -> None:
        self.db = db
        self.settings = settings

    # ═══════════════════════════════════════════════════════════
    #  Provider CRUD
    # ═══════════════════════════════════════════════════════════

    async def list_providers(
        self,
        *,
        page: int = 1,
        size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[ModelProvider], int]:
        q = select(ModelProvider)
        cq = select(func.count()).select_from(ModelProvider)

        if is_active is not None:
            q = q.where(ModelProvider.is_active == is_active)
            cq = cq.where(ModelProvider.is_active == is_active)

        q = q.order_by(ModelProvider.sort_order, ModelProvider.created_at.desc())
        q = q.offset((page - 1) * size).limit(size)

        rows = (await self.db.execute(q)).scalars().all()
        total = (await self.db.execute(cq)).scalar_one()

        # 注入掩码 key（非 ORM 字段，供 Schema 序列化用）
        for r in rows:
            r.api_key_masked = _mask_key(
                decrypt_api_key(r.api_key_enc, self.settings.secret_key)
            ) if r.api_key_enc else ""

        return list(rows), total

    async def get_provider(self, provider_id: UUID) -> ModelProvider:
        q = (
            select(ModelProvider)
            .options(selectinload(ModelProvider.models))
            .where(ModelProvider.id == str(provider_id))
        )
        row = (await self.db.execute(q)).scalar_one_or_none()
        if not row:
            raise NotFoundError(f"供应商 {provider_id} 不存在")

        row.api_key_masked = _mask_key(
            decrypt_api_key(row.api_key_enc, self.settings.secret_key)
        ) if row.api_key_enc else ""

        # 为 ModelProviderDetail schema 注入 model_configs 别名
        row.model_configs = list(row.models)
        return row

    async def create_provider(self, data: ModelProviderCreate) -> ModelProvider:
        row = ModelProvider(
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url,
            api_key_enc=encrypt_api_key(data.api_key, self.settings.secret_key),
            extra_config=data.extra_config,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        self.db.add(row)
        await self.db.flush()

        row.api_key_masked = _mask_key(data.api_key)
        log.info("provider.created", provider_id=row.id, name=row.name)
        return row

    async def update_provider(
        self, provider_id: UUID, data: ModelProviderUpdate
    ) -> ModelProvider:
        row = await self._get_provider_or_404(provider_id)

        patch = data.model_dump(exclude_unset=True)

        # 特殊处理 api_key: 明文 → 加密
        if "api_key" in patch:
            raw_key = patch.pop("api_key")
            if raw_key is not None:
                row.api_key_enc = encrypt_api_key(raw_key, self.settings.secret_key)
                row.api_key_masked = _mask_key(raw_key)

        for k, v in patch.items():
            setattr(row, k, v)

        await self.db.flush()
        if not hasattr(row, "api_key_masked") or not row.api_key_masked:
            row.api_key_masked = _mask_key(
                decrypt_api_key(row.api_key_enc, self.settings.secret_key)
            ) if row.api_key_enc else ""

        log.info("provider.updated", provider_id=str(provider_id))
        return row

    async def delete_provider(self, provider_id: UUID) -> None:
        row = await self._get_provider_or_404(provider_id)

        # 检查是否还有关联的 model configs
        cnt = (
            await self.db.execute(
                select(func.count())
                .select_from(ModelConfig)
                .where(ModelConfig.provider_id == str(provider_id))
            )
        ).scalar_one()
        if cnt > 0:
            raise ConflictError(
                f"供应商下仍有 {cnt} 个模型配置，请先删除模型配置"
            )

        await self.db.delete(row)
        await self.db.flush()
        log.info("provider.deleted", provider_id=str(provider_id))

    async def test_provider_connection(self, provider_id: UUID) -> dict:
        """测试供应商连接"""
        row = await self._get_provider_or_404(provider_id)
        raw_key = (
            decrypt_api_key(row.api_key_enc, self.settings.secret_key)
            if row.api_key_enc
            else ""
        )
        try:
            from infrastructure.external.provider_adapters import (
                ProviderCredentials,
                get_adapter,
            )

            cred = ProviderCredentials(
                api_key=raw_key,
                base_url=row.base_url,
            )
            adapter = get_adapter(row.provider_type, cred)
            result = await adapter.test_connection()
            return {"success": True, "message": result}
        except Exception as exc:
            log.warning(
                "provider.test_failed",
                provider_id=str(provider_id),
                error=str(exc),
            )
            return {"success": False, "message": str(exc)}

    # ═══════════════════════════════════════════════════════════
    #  Model Config CRUD
    # ═══════════════════════════════════════════════════════════

    async def list_model_configs(
        self,
        *,
        page: int = 1,
        size: int = 20,
        provider_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ModelConfig], int]:
        q = select(ModelConfig)
        cq = select(func.count()).select_from(ModelConfig)

        if provider_id is not None:
            q = q.where(ModelConfig.provider_id == str(provider_id))
            cq = cq.where(ModelConfig.provider_id == str(provider_id))
        if is_active is not None:
            q = q.where(ModelConfig.is_active == is_active)
            cq = cq.where(ModelConfig.is_active == is_active)

        q = q.order_by(ModelConfig.sort_order, ModelConfig.created_at.desc())
        q = q.offset((page - 1) * size).limit(size)

        rows = (await self.db.execute(q)).scalars().all()
        total = (await self.db.execute(cq)).scalar_one()
        return list(rows), total

    async def get_model_config(self, config_id: UUID) -> ModelConfig:
        q = (
            select(ModelConfig)
            .options(selectinload(ModelConfig.provider))
            .where(ModelConfig.id == str(config_id))
        )
        row = (await self.db.execute(q)).scalar_one_or_none()
        if not row:
            raise NotFoundError(f"模型配置 {config_id} 不存在")
        return row

    async def create_model_config(self, data: ModelConfigCreate) -> ModelConfig:
        # 验证 provider 存在
        await self._get_provider_or_404(data.provider_id)

        row = ModelConfig(
            provider_id=str(data.provider_id),
            model_name=data.model_name,
            display_name=data.display_name,
            capabilities=data.capabilities,
            default_params=data.default_params,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        self.db.add(row)
        await self.db.flush()
        log.info("model_config.created", config_id=row.id, model=row.model_name)
        return row

    async def update_model_config(
        self, config_id: UUID, data: ModelConfigUpdate
    ) -> ModelConfig:
        row = await self._get_config_or_404(config_id)

        patch = data.model_dump(exclude_unset=True)

        # 如果更换 provider，验证新 provider 存在
        if "provider_id" in patch and patch["provider_id"] is not None:
            await self._get_provider_or_404(patch["provider_id"])
            patch["provider_id"] = str(patch["provider_id"])

        for k, v in patch.items():
            setattr(row, k, v)

        await self.db.flush()
        log.info("model_config.updated", config_id=str(config_id))
        return row

    async def delete_model_config(self, config_id: UUID) -> None:
        row = await self._get_config_or_404(config_id)

        # 检查是否有 binding 引用
        cnt = (
            await self.db.execute(
                select(func.count())
                .select_from(SceneModelBinding)
                .where(SceneModelBinding.model_config_id == str(config_id))
            )
        ).scalar_one()
        if cnt > 0:
            raise ConflictError(
                f"该模型配置仍被 {cnt} 个场景绑定引用，请先解除绑定"
            )

        await self.db.delete(row)
        await self.db.flush()
        log.info("model_config.deleted", config_id=str(config_id))

    # ═══════════════════════════════════════════════════════════
    #  Scene Binding CRUD
    # ═══════════════════════════════════════════════════════════

    async def list_bindings(
        self, *, page: int = 1, size: int = 50
    ) -> tuple[list[SceneModelBinding], int]:
        q = select(SceneModelBinding).order_by(SceneModelBinding.scene_key)
        cq = select(func.count()).select_from(SceneModelBinding)

        q = q.offset((page - 1) * size).limit(size)

        rows = (await self.db.execute(q)).scalars().all()
        total = (await self.db.execute(cq)).scalar_one()
        return list(rows), total

    async def create_binding(
        self, data: SceneModelBindingCreate
    ) -> SceneModelBinding:
        # 验证 model_config 存在
        await self._get_config_or_404(data.model_config_id)

        # 检查 scene_key 唯一性
        existing = (
            await self.db.execute(
                select(SceneModelBinding).where(
                    SceneModelBinding.scene_key == data.scene_key
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"场景 '{data.scene_key}' 已绑定模型配置")

        row = SceneModelBinding(
            scene_key=data.scene_key,
            scene_label=data.scene_label,
            model_config_id=str(data.model_config_id),
            param_overrides=data.param_overrides,
            is_active=data.is_active,
        )
        self.db.add(row)
        await self.db.flush()
        _invalidate_cache(data.scene_key)
        log.info("binding.created", scene_key=data.scene_key)
        return row

    async def update_binding(
        self, scene_key: str, data: SceneModelBindingUpdate
    ) -> SceneModelBinding:
        row = await self._get_binding_or_404(scene_key)

        patch = data.model_dump(exclude_unset=True)

        if "model_config_id" in patch and patch["model_config_id"] is not None:
            await self._get_config_or_404(patch["model_config_id"])
            patch["model_config_id"] = str(patch["model_config_id"])

        for k, v in patch.items():
            setattr(row, k, v)

        await self.db.flush()
        _invalidate_cache(scene_key)
        log.info("binding.updated", scene_key=scene_key)
        return row

    async def delete_binding(self, scene_key: str) -> None:
        row = await self._get_binding_or_404(scene_key)
        await self.db.delete(row)
        await self.db.flush()
        _invalidate_cache(scene_key)
        log.info("binding.deleted", scene_key=scene_key)

    # ═══════════════════════════════════════════════════════════
    #  场景解析 — 供业务调用
    # ═══════════════════════════════════════════════════════════

    async def resolve_model(self, scene_key: str) -> ResolvedModel:
        """根据 scene_key 解析出完整的模型配置，带 5min 内存缓存"""

        # 检查缓存
        now = time.monotonic()
        cached = _resolve_cache.get(scene_key)
        if cached and (now - cached[0]) < _CACHE_TTL:
            return cached[1]

        # 查询绑定 → 模型配置 → 供应商（三表 JOIN）
        q = (
            select(SceneModelBinding, ModelConfig, ModelProvider)
            .join(ModelConfig, SceneModelBinding.model_config_id == ModelConfig.id)
            .join(ModelProvider, ModelConfig.provider_id == ModelProvider.id)
            .where(
                SceneModelBinding.scene_key == scene_key,
                SceneModelBinding.is_active.is_(True),
                ModelConfig.is_active.is_(True),
                ModelProvider.is_active.is_(True),
            )
        )
        result = (await self.db.execute(q)).one_or_none()

        # 回退到 __default__
        if result is None and scene_key != "__default__":
            log.info("resolve.fallback", scene_key=scene_key, fallback="__default__")
            return await self.resolve_model("__default__")

        if result is None:
            raise NotFoundError(
                f"场景 '{scene_key}' 未绑定模型配置，且无默认配置"
            )

        binding, config, provider = result

        # 合并参数：default_params ← param_overrides
        merged = {**config.default_params, **binding.param_overrides}

        resolved = ResolvedModel(
            scene_key=scene_key,
            provider_type=provider.provider_type,
            model_name=config.model_name,
            api_key=decrypt_api_key(provider.api_key_enc, self.settings.secret_key),
            base_url=provider.base_url,
            extra_config=provider.extra_config,
            temperature=merged.get("temperature", 0.7),
            max_tokens=merged.get("max_tokens"),
            extra_params={
                k: v for k, v in merged.items()
                if k not in ("temperature", "max_tokens")
            },
        )

        _resolve_cache[scene_key] = (now, resolved)
        return resolved

    # ═══════════════════════════════════════════════════════════
    #  内部辅助
    # ═══════════════════════════════════════════════════════════

    async def _get_provider_or_404(self, provider_id: UUID) -> ModelProvider:
        row = (
            await self.db.execute(
                select(ModelProvider).where(ModelProvider.id == str(provider_id))
            )
        ).scalar_one_or_none()
        if not row:
            raise NotFoundError(f"供应商 {provider_id} 不存在")
        return row

    async def _get_config_or_404(self, config_id: UUID) -> ModelConfig:
        row = (
            await self.db.execute(
                select(ModelConfig).where(ModelConfig.id == str(config_id))
            )
        ).scalar_one_or_none()
        if not row:
            raise NotFoundError(f"模型配置 {config_id} 不存在")
        return row

    async def _get_binding_or_404(self, scene_key: str) -> SceneModelBinding:
        row = (
            await self.db.execute(
                select(SceneModelBinding).where(
                    SceneModelBinding.scene_key == scene_key
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise NotFoundError(f"场景绑定 '{scene_key}' 不存在")
        return row