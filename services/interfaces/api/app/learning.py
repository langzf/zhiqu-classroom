"""App 学习路由 — 任务 / 进度 / 学习会话 / 掌握度"""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query

from shared.response import ok, paged
from interfaces.schemas.learning import (
    TaskOut, TaskDetail,
    ProgressStart, ProgressSubmit, ProgressOut,
    LearningTaskOut, LearningTaskCreate, LearningTaskUpdate,
    MasteryRecordOut,
    StudySessionCreate, StudySessionOut,
)
from interfaces.api.deps import CurrentUser, StudentUser, LearningSvc, LearningCoreSvc

router = APIRouter(prefix="/api/v1/app/learning", tags=["app-learning"])


# ── 任务编排（学生视角）──────────────────────────────────

@router.get("/tasks", summary="我的任务列表")
async def my_tasks(
    user: CurrentUser,
    svc: LearningSvc,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_tasks_for_student(
        student_id=user.sub, status=status,
        page=page, page_size=page_size,
    )
    data = [TaskOut.model_validate(t).model_dump() for t in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.get("/tasks/{task_id}", summary="任务详情")
async def get_task(task_id: UUID, user: CurrentUser, svc: LearningSvc):
    task = await svc.get_task(task_id)
    return ok(TaskDetail.model_validate(task).model_dump())


@router.post("/tasks/{task_id}/start", summary="开始任务")
async def start_task(task_id: UUID, user: CurrentUser, svc: LearningSvc):
    progress = await svc.start_progress(task_id, student_id=user.sub)
    return ok(ProgressOut.model_validate(progress).model_dump())


@router.post("/tasks/{task_id}/submit", summary="提交任务进度")
async def submit_task(
    task_id: UUID, body: ProgressSubmit,
    user: CurrentUser, svc: LearningSvc,
):
    progress = await svc.submit_progress(task_id, student_id=user.sub, data=body)
    return ok(ProgressOut.model_validate(progress).model_dump())


# ── 学习任务（原 learning_core，学生端）─────────────────

@router.get("/learning-tasks", summary="我的学习任务")
async def my_learning_tasks(
    user: CurrentUser,
    svc: LearningCoreSvc,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_tasks(
        student_id=user.sub, status=status,
        page=page, page_size=page_size,
    )
    data = [LearningTaskOut.model_validate(t).model_dump() for t in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.post("/learning-tasks/{task_id}/submit", summary="提交学习任务答案")
async def submit_learning_task(
    task_id: UUID, body: LearningTaskUpdate, user: CurrentUser, svc: LearningCoreSvc,
):
    result = await svc.submit_task(
        task_id,
        score=body.score or 0,
        answer_snapshot=body.answer_snapshot,
    )
    return ok(LearningTaskOut.model_validate(result).model_dump())


# ── 掌握度 ────────────────────────────────────────────

@router.get("/mastery", summary="我的知识点掌握度")
async def my_mastery(
    user: CurrentUser,
    svc: LearningCoreSvc,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_mastery(
        student_id=user.sub, page=page, page_size=page_size,
    )
    data = [MasteryRecordOut.model_validate(m).model_dump() for m in items]
    return paged(data, total=total, page=page, page_size=page_size)


# ── 学习会话 ──────────────────────────────────────────

@router.post("/study-sessions", summary="记录学习会话")
async def create_study_session(
    body: StudySessionCreate, user: CurrentUser, svc: LearningCoreSvc,
):
    session = await svc.create_study_session(
        student_id=user.sub,
        knowledge_point_id=body.knowledge_point_id,
        session_type=body.session_type,
    )
    return ok(StudySessionOut.model_validate(session).model_dump())


@router.get("/study-sessions", summary="学习会话列表")
async def list_study_sessions(
    user: CurrentUser,
    svc: LearningCoreSvc,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_study_sessions(
        student_id=user.sub, page=page, page_size=page_size,
    )
    data = [StudySessionOut.model_validate(s).model_dump() for s in items]
    return paged(data, total=total, page=page, page_size=page_size)


# ── 学习概览 ──────────────────────────────────────────

@router.get("/progress", summary="学习进度概览")
async def my_progress(user: CurrentUser, svc: LearningCoreSvc):
    stats = await svc.get_student_progress(student_id=user.sub)
    return ok(stats)
