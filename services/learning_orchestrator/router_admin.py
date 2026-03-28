"""学习编排 — Admin 路由

前缀: /api/v1/admin/learning
管理员：学习任务 CRUD、查看任何学生进度。
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from database import get_db
from deps import require_role
from shared.schemas import ok, paged
from shared.security import TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from learning_orchestrator.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskItemCreate,
    TaskOut,
    TaskItemOut,
    ProgressOut,
)
from learning_orchestrator.service import LearningService

router = APIRouter(prefix="/learning", tags=["admin-learning"])


# ── 内部依赖 ──────────────────────────────────────────

def _build_service(db: AsyncSession = Depends(get_db)) -> LearningService:
    return LearningService(db=db)

Svc = Annotated[LearningService, Depends(_build_service)]
AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 任务 CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/tasks")
async def create_task(body: TaskCreate, user: AdminUser, svc: Svc):
    task = await svc.create_task(body, created_by=user.sub)
    return ok(TaskOut.model_validate(task).model_dump())


@router.get("/tasks")
async def list_tasks(
    user: AdminUser,
    svc: Svc,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_tasks(status=status, page=page, page_size=page_size)
    return paged(
        items=[TaskOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: UUID, user: AdminUser, svc: Svc):
    task = await svc.get_task(str(task_id))
    return ok(TaskOut.model_validate(task).model_dump())


@router.patch("/tasks/{task_id}")
async def update_task(task_id: UUID, body: TaskUpdate, user: AdminUser, svc: Svc):
    task = await svc.update_task(str(task_id), **body.model_dump(exclude_unset=True))
    return ok(TaskOut.model_validate(task).model_dump())


@router.post("/tasks/{task_id}/publish")
async def publish_task(task_id: UUID, user: AdminUser, svc: Svc):
    """发布任务（状态 → published）"""
    task = await svc.publish_task(str(task_id))
    return ok(TaskOut.model_validate(task).model_dump())


@router.post("/tasks/{task_id}/archive")
async def archive_task(task_id: UUID, user: AdminUser, svc: Svc):
    """归档任务（状态 → archived）"""
    task = await svc.archive_task(str(task_id))
    return ok(TaskOut.model_validate(task).model_dump())


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: UUID, user: AdminUser, svc: Svc):
    """软删除任务"""
    await svc.soft_delete_task(str(task_id))
    return ok({"task_id": str(task_id), "deleted": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 任务子项
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/tasks/{task_id}/items")
async def add_task_items(task_id: UUID, body: TaskItemCreate, user: AdminUser, svc: Svc):
    items = await svc.add_task_items(str(task_id), body)
    return ok([TaskItemOut.model_validate(i).model_dump() for i in items])


@router.get("/tasks/{task_id}/items")
async def get_task_items(task_id: UUID, user: AdminUser, svc: Svc):
    items = await svc.get_task_items(str(task_id))
    return ok([TaskItemOut.model_validate(i).model_dump() for i in items])


@router.delete("/tasks/{task_id}/items/{item_id}")
async def remove_task_item(task_id: UUID, item_id: UUID, user: AdminUser, svc: Svc):
    """删除任务子项"""
    await svc.remove_task_item(str(item_id))
    return ok({"task_id": str(task_id), "item_id": str(item_id), "deleted": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 进度查看（管理员查看任意学生）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/tasks/{task_id}/progress")
async def get_task_progress(task_id: UUID, user: AdminUser, svc: Svc):
    """查看某任务下所有学生的进度汇总"""
    progress = await svc.get_task_progress(str(task_id))
    return ok([ProgressOut.model_validate(p).model_dump() for p in progress])


@router.get("/tasks/{task_id}/progress/{student_id}")
async def get_student_progress(
    task_id: UUID, student_id: UUID, user: AdminUser, svc: Svc,
):
    progress = await svc.get_progress(str(task_id), str(student_id))
    return ok(ProgressOut.model_validate(progress).model_dump())
