"""Admin 学习任务管理路由 — 任务编排 + 学习任务"""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query

from shared.response import ok, paged
from interfaces.schemas.learning import (
    TaskCreate, TaskUpdate, TaskOut, TaskDetail,
    TaskItemCreate, TaskItemUpdate, TaskItemOut,
    ProgressOut,
    LearningTaskCreate, LearningTaskUpdate, LearningTaskOut,
)
from interfaces.api.deps import AdminUser, LearningSvc, LearningCoreSvc

router = APIRouter(prefix="/api/v1/admin/learning", tags=["admin-learning"])


# ── 任务编排（原 learning_orchestrator）─────────────────

@router.post("/tasks", summary="创建任务（含子项）")
async def create_task(body: TaskCreate, svc: LearningSvc, admin: AdminUser):
    task = await svc.create_task(body, created_by=admin.sub)
    return ok(TaskOut.model_validate(task).model_dump())


@router.get("/tasks", summary="任务列表")
async def list_tasks(
    svc: LearningSvc,
    _admin: AdminUser,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_tasks(status=status, page=page, page_size=page_size)
    data = [TaskOut.model_validate(t).model_dump() for t in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.get("/tasks/{task_id}", summary="任务详情（含子项）")
async def get_task(task_id: UUID, svc: LearningSvc, _admin: AdminUser):
    task = await svc.get_task(task_id)
    return ok(TaskDetail.model_validate(task).model_dump())


@router.patch("/tasks/{task_id}", summary="更新任务")
async def update_task(
    task_id: UUID, body: TaskUpdate, svc: LearningSvc, _admin: AdminUser,
):
    task = await svc.update_task(task_id, body)
    return ok(TaskOut.model_validate(task).model_dump())


@router.delete("/tasks/{task_id}", summary="删除任务（软删除）")
async def delete_task(task_id: UUID, svc: LearningSvc, _admin: AdminUser):
    await svc.delete_task(task_id)
    return ok()


@router.post("/tasks/{task_id}/publish", summary="发布任务")
async def publish_task(task_id: UUID, svc: LearningSvc, _admin: AdminUser):
    task = await svc.publish_task(task_id)
    return ok(TaskOut.model_validate(task).model_dump())


# ── 任务子项 ──────────────────────────────────────────


@router.get("/tasks/{task_id}/items", summary="子项列表")
async def list_task_items(task_id: UUID, svc: LearningSvc, _admin: AdminUser):
    items = await svc.list_items(str(task_id))
    data = [TaskItemOut.model_validate(i).model_dump() for i in items]
    return ok(data)


@router.post("/tasks/{task_id}/items", summary="添加子项")
async def add_task_item(
    task_id: UUID, body: TaskItemCreate, svc: LearningSvc, _admin: AdminUser,
):
    item = await svc.add_item(str(task_id), body)
    return ok(TaskItemOut.model_validate(item).model_dump())


@router.patch("/tasks/{task_id}/items/{item_id}", summary="更新子项")
async def update_task_item(
    task_id: UUID, item_id: UUID, body: TaskItemUpdate,
    svc: LearningSvc, _admin: AdminUser,
):
    item = await svc.update_item(str(task_id), str(item_id), body)
    return ok(TaskItemOut.model_validate(item).model_dump())


@router.delete("/tasks/{task_id}/items/{item_id}", summary="删除子项")
async def delete_task_item(
    task_id: UUID, item_id: UUID, svc: LearningSvc, _admin: AdminUser,
):
    await svc.delete_item(str(task_id), str(item_id))
    return ok()


# ── 任务进度（管理员查看）──────────────────────────────


@router.get("/tasks/{task_id}/progress", summary="任务进度列表")
async def list_task_progress(
    task_id: UUID, svc: LearningSvc, _admin: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_task_progress(
        str(task_id), page=page, page_size=page_size,
    )
    data = [ProgressOut.model_validate(p).model_dump() for p in items]
    return paged(data, total=total, page=page, page_size=page_size)


# ── 学习任务（原 learning_core）────────────────────────

@router.post("/learning-tasks", summary="创建学习任务")
async def create_learning_task(
    body: LearningTaskCreate, svc: LearningCoreSvc, admin: AdminUser,
):
    task = await svc.create_task(body, created_by=admin.sub)
    return ok(LearningTaskOut.model_validate(task).model_dump())


@router.get("/learning-tasks", summary="学习任务列表（管理员查所有）")
async def list_learning_tasks(
    svc: LearningCoreSvc,
    _admin: AdminUser,
    student_id: Optional[UUID] = Query(None, description="按学生筛选"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_tasks(
        student_id=student_id, status=status,
        page=page, page_size=page_size,
    )
    data = [LearningTaskOut.model_validate(t).model_dump() for t in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.patch("/learning-tasks/{task_id}", summary="更新学习任务")
async def update_learning_task(
    task_id: UUID, body: LearningTaskUpdate,
    svc: LearningCoreSvc, _admin: AdminUser,
):
    task = await svc.update_task(task_id, body)
    return ok(LearningTaskOut.model_validate(task).model_dump())
