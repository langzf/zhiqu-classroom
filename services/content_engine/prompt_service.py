"""Prompt 模板管理 Service"""

import uuid
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from content_engine.models import PromptTemplate
from shared.exceptions import NotFoundError


async def create_prompt_template(
    db: AsyncSession,
    *,
    resource_type: str,
    name: str,
    template_text: str,
    description: Optional[str] = None,
    is_active: bool = True,
) -> PromptTemplate:
    tpl = PromptTemplate(
        resource_type=resource_type,
        name=name,
        template_text=template_text,
        description=description,
        is_active=is_active,
        version=1,
    )
    db.add(tpl)
    await db.flush()
    await db.refresh(tpl)
    return tpl


async def get_prompt_template(db: AsyncSession, tpl_id: uuid.UUID) -> PromptTemplate:
    tpl = await db.get(PromptTemplate, tpl_id)
    if not tpl or tpl.is_deleted:
        raise NotFoundError("prompt_template", str(tpl_id))
    return tpl


async def get_active_template(db: AsyncSession, resource_type: str) -> PromptTemplate:
    """获取某 resource_type 当前激活的模板"""
    stmt = (
        select(PromptTemplate)
        .where(
            and_(
                PromptTemplate.resource_type == resource_type,
                PromptTemplate.is_active.is_(True),
                PromptTemplate.deleted_at.is_(None),
            )
        )
        .order_by(PromptTemplate.version.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise NotFoundError("active_prompt_template", resource_type)
    return tpl


async def list_prompt_templates(
    db: AsyncSession,
    resource_type: Optional[str] = None,
    active_only: bool = False,
) -> list[PromptTemplate]:
    stmt = select(PromptTemplate).where(PromptTemplate.deleted_at.is_(None))
    if resource_type:
        stmt = stmt.where(PromptTemplate.resource_type == resource_type)
    if active_only:
        stmt = stmt.where(PromptTemplate.is_active.is_(True))
    stmt = stmt.order_by(PromptTemplate.resource_type, PromptTemplate.version.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_prompt_template(
    db: AsyncSession,
    tpl_id: uuid.UUID,
    **kwargs,
) -> PromptTemplate:
    tpl = await get_prompt_template(db, tpl_id)
    for k, v in kwargs.items():
        if hasattr(tpl, k) and v is not None:
            setattr(tpl, k, v)
    await db.flush()
    await db.refresh(tpl)
    return tpl


async def activate_template(
    db: AsyncSession, tpl_id: uuid.UUID
) -> PromptTemplate:
    """激活某模板，同时停用同 resource_type 的其他模板"""
    tpl = await get_prompt_template(db, tpl_id)
    # 停用同类型其他模板
    siblings = await list_prompt_templates(db, resource_type=tpl.resource_type)
    for s in siblings:
        if s.id != tpl.id:
            s.is_active = False
    tpl.is_active = True
    await db.flush()
    await db.refresh(tpl)
    return tpl
