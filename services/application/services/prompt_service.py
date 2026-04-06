"""
Prompt 模板 业务逻辑
─────────────────────
管理 LLM prompt 模板的 CRUD
"""

from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models import PromptTemplate
from infrastructure.persistence.models.base import generate_uuid7
from shared.exceptions import ConflictError, NotFoundError

logger = structlog.get_logger()


class PromptService:
    """Prompt 模板管理"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_template(self, data: dict) -> PromptTemplate:
        """创建 prompt 模板"""
        # code 唯一性校验
        existing = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.code == data["code"])
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"模板 code '{data['code']}' 已存在")

        tpl = PromptTemplate(id=str(generate_uuid7()), **data)
        self.db.add(tpl)
        await self.db.flush()
        await self.db.refresh(tpl)
        logger.info("prompt_template_created", code=tpl.code)
        return tpl

    async def get_template(self, template_id: str) -> PromptTemplate:
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        result = await self.db.execute(stmt)
        tpl = result.scalar_one_or_none()
        if not tpl:
            raise NotFoundError("prompt_template", template_id)
        return tpl

    async def get_template_by_code(self, code: str) -> PromptTemplate:
        stmt = select(PromptTemplate).where(
            PromptTemplate.code == code,
            PromptTemplate.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        tpl = result.scalar_one_or_none()
        if not tpl:
            raise NotFoundError("prompt_template_code", code)
        return tpl

    async def list_templates(
        self,
        scene: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PromptTemplate], int]:
        base = select(PromptTemplate)
        if scene:
            base = base.where(PromptTemplate.scene == scene)
        if is_active is not None:
            base = base.where(PromptTemplate.is_active == is_active)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(PromptTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def update_template(self, template_id: str, **kwargs) -> PromptTemplate:
        tpl = await self.get_template(template_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(tpl, k):
                setattr(tpl, k, v)
        await self.db.flush()
        await self.db.refresh(tpl)
        logger.info(
            "prompt_template_updated",
            template_id=template_id,
            fields=list(kwargs.keys()),
        )
        return tpl

    async def delete_template(self, template_id: str) -> PromptTemplate:
        tpl = await self.get_template(template_id)
        tpl.is_active = False
        await self.db.flush()
        await self.db.refresh(tpl)
        logger.info("prompt_template_deactivated", template_id=template_id)
        return tpl
