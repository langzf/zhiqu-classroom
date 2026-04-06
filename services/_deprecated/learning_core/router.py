"""
learning_core 路由
─────────────────
前缀: /api/v1/learning
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import TokenPayload, get_current_user, require_role
from shared.schemas import ok, paged

from .schemas import (
    LearningTaskCreate,
    LearningTaskOut,
    LearningTaskUpdate,
    MasteryRecordOut,
    StudySessionCreate,
    StudySessionOut,
)
from .service import LearningService

router = APIRouter(prefix="/api/v1/learning", tags=["learning-core"])


# ── 依赖 ──────────────────────────────────────────────


async def _build_service(db: AsyncSession = Depends(get_db)):
    return LearningService(db)


Svc = Annotated[LearningService, Depends(_build_service)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]


# ── 学习任务 ──────────────────────────────────────────


@router.post("/tasks")
async def create_task(body: LearningTaskCreate, svc: Svc, user: CurrentUser):
    """创建学习任务（管理员/教师发布，或学生自主创建）"""
    task = await svc.create_task(
        student_id=str(body.student_id),
        knowledge_point_id=str(body.knowledge_point_id),
        task_type=body.task_type,
        source_resource_id=str(body.source_resource_id) if body.source_resource_id else None,
        due_date=body.due_date,
    )
    return ok(LearningTaskOut.model_validate(task).model_dump())


@router.get("/tasks")
async def list_tasks(
    svc: Svc,
    user: CurrentUser,
    student_id: Optional[str] = Query(None, description="学生 ID（管理员可查他人）"),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询学习任务列表"""
    # 普通学生只能查自己的
    target_id = student_id if (user.role == "admin" and student_id) else user.sub
    items, total = await svc.list_tasks(
        student_id=target_id,
        status=status,
        task_type=task_type,
        page=page,
        page_size=page_size,
    )
    data = [LearningTaskOut.model_validate(t).model_dump() for t in items]
    return paged(data, total, page, page_size)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, svc: Svc, user: CurrentUser):
    """获取任务详情"""
    task = await svc.get_task(task_id)
    return ok(LearningTaskOut.model_validate(task).model_dump())


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    body: LearningTaskUpdate,
    svc: Svc,
    user: CurrentUser,
):
    """更新任务"""
    update_data = body.model_dump(exclude_unset=True)
    task = await svc.update_task(task_id, **update_data)
    return ok(LearningTaskOut.model_validate(task).model_dump())


@router.post("/tasks/{task_id}/submit")
async def submit_task(
    task_id: str,
    svc: Svc,
    user: CurrentUser,
    score: int = Query(..., ge=0, le=100),
    answer_snapshot: Optional[dict] = None,
):
    """学生提交任务"""
    task = await svc.submit_task(
        task_id=task_id,
        score=score,
        answer_snapshot=answer_snapshot,
    )
    return ok(LearningTaskOut.model_validate(task).model_dump())


# ── 掌握度 ───────────────────────────────────────────


@router.get("/mastery")
async def list_mastery(
    svc: Svc,
    user: CurrentUser,
    student_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """查看学生掌握度列表"""
    target_id = student_id if (user.role == "admin" and student_id) else user.sub
    items, total = await svc.list_mastery(
        student_id=target_id, page=page, page_size=page_size
    )
    data = [MasteryRecordOut.model_validate(m).model_dump() for m in items]
    return paged(data, total, page, page_size)


@router.get("/mastery/{knowledge_point_id}")
async def get_mastery(
    knowledge_point_id: str,
    svc: Svc,
    user: CurrentUser,
    student_id: Optional[str] = Query(None),
):
    """查看某知识点掌握度"""
    target_id = student_id if (user.role == "admin" and student_id) else user.sub
    record = await svc.get_mastery(
        student_id=target_id,
        knowledge_point_id=knowledge_point_id,
    )
    if not record:
        return ok(None)
    return ok(MasteryRecordOut.model_validate(record).model_dump())


# ── 学习会话 ──────────────────────────────────────────


@router.post("/sessions")
async def create_study_session(
    body: StudySessionCreate, svc: Svc, user: CurrentUser
):
    """开始一个学习会话"""
    session = await svc.create_study_session(
        student_id=str(body.student_id),
        knowledge_point_id=str(body.knowledge_point_id) if body.knowledge_point_id else None,
        session_type=body.session_type,
    )
    return ok(StudySessionOut.model_validate(session).model_dump())


@router.patch("/sessions/{session_id}")
async def update_study_session(
    session_id: str,
    svc: Svc,
    user: CurrentUser,
    duration_seconds: Optional[int] = Query(None, ge=0),
):
    """更新学习会话（结束时上报时长）"""
    session = await svc.update_study_session(
        session_id=session_id,
        duration_seconds=duration_seconds,
    )
    return ok(StudySessionOut.model_validate(session).model_dump())


@router.get("/sessions")
async def list_study_sessions(
    svc: Svc,
    user: CurrentUser,
    student_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查看学习会话列表"""
    target_id = student_id if (user.role == "admin" and student_id) else user.sub
    items, total = await svc.list_study_sessions(
        student_id=target_id, page=page, page_size=page_size
    )
    data = [StudySessionOut.model_validate(s).model_dump() for s in items]
    return paged(data, total, page, page_size)


# ── 进度概览 ──────────────────────────────────────────


@router.get("/progress")
async def get_progress(
    svc: Svc,
    user: CurrentUser,
    student_id: Optional[str] = Query(None),
):
    """获取学习进度概览"""
    target_id = student_id if (user.role == "admin" and student_id) else user.sub
    progress = await svc.get_student_progress(student_id=target_id)
    return ok(progress)
