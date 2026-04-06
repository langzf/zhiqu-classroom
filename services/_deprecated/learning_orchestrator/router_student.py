"""学习编排 — 学生端路由

前缀: /api/v1/learning
学生查看自己的任务和提交进度。
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from database import get_db
from deps import get_current_user
from shared.schemas import ok, paged
from shared.security import TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from learning_orchestrator.schemas import (
    ProgressSubmit,
    TaskOut,
    TaskItemOut,
    ProgressOut,
)
from learning_orchestrator.service import LearningService

router = APIRouter(prefix="/learning", tags=["student-learning"])


# ── 内部依赖 ──────────────────────────────────────────

def _build_service(db: AsyncSession = Depends(get_db)) -> LearningService:
    return LearningService(db=db)

Svc = Annotated[LearningService, Depends(_build_service)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 我的任务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/tasks")
async def list_my_tasks(
    user: CurrentUser,
    svc: Svc,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """学生查看分配给自己的任务"""
    items, total = await svc.list_tasks(
        status=status,
        page=page, page_size=page_size,
    )
    return paged(
        items=[TaskOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: UUID, user: CurrentUser, svc: Svc):
    task = await svc.get_task(str(task_id))
    return ok(TaskOut.model_validate(task).model_dump())


@router.get("/tasks/{task_id}/items")
async def get_task_items(task_id: UUID, user: CurrentUser, svc: Svc):
    items = await svc.get_task_items(str(task_id))
    return ok([TaskItemOut.model_validate(i).model_dump() for i in items])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 进度提交 & 查看
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: UUID, user: CurrentUser, svc: Svc,
):
    """学生开始任务"""
    progress = await svc.start_task(str(task_id), user.sub)
    return ok(ProgressOut.model_validate(progress).model_dump())


@router.post("/tasks/{task_id}/submit")
async def submit_task(
    task_id: UUID, body: ProgressSubmit, user: CurrentUser, svc: Svc,
):
    """学生提交学习进度"""
    item_results = [r.model_dump() for r in body.item_results] if body.item_results else None
    progress = await svc.submit_task(str(task_id), user.sub, item_results=item_results)
    return ok(ProgressOut.model_validate(progress).model_dump())


@router.get("/tasks/{task_id}/progress")
async def get_my_progress(task_id: UUID, user: CurrentUser, svc: Svc):
    """学生查看自己在某任务的进度"""
    progress = await svc.get_progress(str(task_id), user.sub)
    return ok(ProgressOut.model_validate(progress).model_dump())
