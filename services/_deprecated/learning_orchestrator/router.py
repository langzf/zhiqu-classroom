"""
learning_orchestrator 路由
──────────────────────────
路径前缀：/api/v1/learning
分区：管理端（🛡️ admin）+ 学生端（👤 all）
"""

from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user, require_admin
from shared.exceptions import ForbiddenError
from shared.schemas import ok, paged
from shared.security import TokenPayload

from learning_orchestrator.schemas import (
    ProgressOut,
    ProgressSubmit,
    TaskCreate,
    TaskDetail,
    TaskItemCreate,
    TaskItemOut,
    TaskOut,
    TaskUpdate,
)
from learning_orchestrator.service import LearningService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/learning", tags=["learning-orchestrator"])


# ── 内部依赖 ──────────────────────────────────────────


def _build_service(db: AsyncSession = Depends(get_db)) -> LearningService:
    return LearningService(db=db)


Svc = Annotated[LearningService, Depends(_build_service)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
AdminUser = Annotated[TokenPayload, Depends(require_admin)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 管理端 — 任务 CRUD（🛡️ admin）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/tasks")
async def create_task(body: TaskCreate, user: AdminUser, svc: Svc):
    """🛡️ 创建学习任务"""
    task = await svc.create_task(
        created_by=user.sub,
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        subject=body.subject,
        grade_range=body.grade_range,
        publish_at=body.publish_at,
        deadline=body.deadline,
        config=body.config,
        items=[item.model_dump() for item in body.items],
    )
    return ok(TaskDetail.model_validate(task).model_dump())


@router.get("/tasks")
async def list_tasks(
    user: AdminUser,
    svc: Svc,
    status: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """🛡️ 任务列表（管理端，支持筛选）"""
    items, total = await svc.list_tasks(
        status=status,
        subject=subject,
        task_type=task_type,
        page=page,
        page_size=page_size,
    )
    return paged(
        items=[TaskOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, user: CurrentUser, svc: Svc):
    """获取任务详情（含子项）"""
    task = await svc.get_task(task_id)
    return ok(TaskDetail.model_validate(task).model_dump())


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate, user: AdminUser, svc: Svc):
    """🛡️ 更新任务"""
    update_data = body.model_dump(exclude_unset=True)
    task = await svc.update_task(task_id, **update_data)
    return ok(TaskDetail.model_validate(task).model_dump())


@router.post("/tasks/{task_id}/publish")
async def publish_task(task_id: str, user: AdminUser, svc: Svc):
    """🛡️ 发布任务"""
    task = await svc.publish_task(task_id)
    return ok(TaskOut.model_validate(task).model_dump())


@router.post("/tasks/{task_id}/archive")
async def archive_task(task_id: str, user: AdminUser, svc: Svc):
    """🛡️ 归档任务"""
    task = await svc.archive_task(task_id)
    return ok(TaskOut.model_validate(task).model_dump())


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: AdminUser, svc: Svc):
    """🛡️ 软删除任务"""
    await svc.soft_delete_task(task_id)
    return ok({"task_id": task_id, "deleted": True})


# ── 任务子项管理（🛡️ admin）────────────────────────────


@router.post("/tasks/{task_id}/items")
async def add_task_item(task_id: str, body: TaskItemCreate, user: AdminUser, svc: Svc):
    """🛡️ 添加任务子项"""
    item = await svc.add_task_item(task_id, body.model_dump())
    return ok(TaskItemOut.model_validate(item).model_dump())


@router.delete("/tasks/{task_id}/items/{item_id}")
async def remove_task_item(
    task_id: str, item_id: str, user: AdminUser, svc: Svc
):
    """🛡️ 删除任务子项"""
    await svc.remove_task_item(item_id)
    return ok({"item_id": item_id, "deleted": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 学生端 — 任务浏览 & 进度（👤 all）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/student/tasks")
async def list_student_tasks(
    user: CurrentUser,
    svc: Svc,
    subject: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """👤 学生可见的已发布任务列表"""
    items, total = await svc.list_tasks(
        status="published",
        subject=subject,
        page=page,
        page_size=page_size,
    )
    return paged(
        items=[TaskOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/student/tasks/{task_id}/start")
async def start_task(task_id: str, user: CurrentUser, svc: Svc):
    """👤 学生开始任务"""
    progress = await svc.start_task(task_id=task_id, student_id=user.sub)
    return ok(ProgressOut.model_validate(progress).model_dump())


@router.post("/student/tasks/{task_id}/submit")
async def submit_task(task_id: str, body: ProgressSubmit, user: CurrentUser, svc: Svc):
    """👤 学生提交任务完成"""
    progress = await svc.submit_task(
        task_id=task_id,
        student_id=user.sub,
        item_results=[ir.model_dump() for ir in body.item_results],
    )
    return ok(ProgressOut.model_validate(progress).model_dump())


@router.get("/student/tasks/{task_id}/progress")
async def get_task_progress(task_id: str, user: CurrentUser, svc: Svc):
    """👤 获取我的任务进度"""
    progress = await svc.get_progress(task_id=task_id, student_id=user.sub)
    return ok(ProgressOut.model_validate(progress).model_dump())


@router.get("/student/progress")
async def list_my_progress(
    user: CurrentUser,
    svc: Svc,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """👤 我的所有任务进度"""
    items, total = await svc.list_student_progress(
        student_id=user.sub,
        status=status,
        page=page,
        page_size=page_size,
    )
    return paged(
        items=[ProgressOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )
