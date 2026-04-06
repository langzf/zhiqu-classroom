"""
Learning schemas（合并 learning_orchestrator + learning_core）
──────────────────────────────────────────────────────────────
任务编排：Task / TaskItem / Progress
学习核心：LearningTask / StudySession / MasteryRecord
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field

from interfaces.schemas.base import OrmBase


# ══════════════════════════════════════════════════════
#  Learning Orchestrator — 任务编排
# ══════════════════════════════════════════════════════


# ── Task ──────────────────────────────────────────────


class TaskItemCreate(BaseModel):
    """创建任务子项"""

    item_type: str = Field(
        ..., description="类型: game|video_script|quiz|reading|ai_chat"
    )
    resource_id: Optional[str] = None
    knowledge_point_id: Optional[str] = None
    title: str = Field(..., max_length=200)
    config: Optional[dict] = None
    sort_order: int = 0


class TaskItemUpdate(BaseModel):
    """更新任务子项（部分更新）"""

    item_type: Optional[str] = None
    resource_id: Optional[str] = None
    knowledge_point_id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    config: Optional[dict] = None
    sort_order: Optional[int] = None


class TaskCreate(BaseModel):
    """创建学习任务（🛡️ admin）"""

    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    task_type: str = Field(
        default="homework",
        description="类型: homework|review|practice|exploration",
    )
    subject: Optional[str] = None
    grade_range: Optional[str] = None
    publish_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    config: Optional[dict] = None
    items: list[TaskItemCreate] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    """更新学习任务（部分更新，🛡️ admin）"""

    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    task_type: Optional[str] = None
    subject: Optional[str] = None
    grade_range: Optional[str] = None
    publish_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    config: Optional[dict] = None
    status: Optional[str] = Field(None, description="draft|published|archived")


class TaskItemOut(OrmBase):
    """任务子项响应"""

    id: UUID
    task_id: str
    item_type: str
    resource_id: Optional[str]
    knowledge_point_id: Optional[str]
    title: str
    config: Optional[dict]
    sort_order: int


class TaskOut(OrmBase):
    """任务响应（列表用，不含子项）"""

    id: UUID
    title: str
    description: Optional[str]
    task_type: str
    status: str
    created_by: str
    subject: Optional[str]
    grade_range: Optional[str]
    publish_at: Optional[datetime]
    deadline: Optional[datetime]
    config: Optional[dict]
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskOut):
    """任务详情（含子项列表）"""

    items: list[TaskItemOut] = []


# ── Progress ──────────────────────────────────────────


class ProgressStart(BaseModel):
    """学生开始任务"""

    pass  # task_id 从路径获取，student_id 从 JWT 获取


class ProgressItemSubmit(BaseModel):
    """提交单个子项完成结果"""

    item_id: str
    score: Optional[int] = Field(None, ge=0, le=100)
    answer_data: Optional[dict] = None


class ProgressSubmit(BaseModel):
    """提交任务完成"""

    item_results: list[ProgressItemSubmit] = Field(default_factory=list)


class ProgressOut(OrmBase):
    """任务进度响应"""

    id: UUID
    task_id: str
    student_id: str
    status: str
    score: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    item_progress: Optional[dict]
    created_at: datetime
    updated_at: datetime


# ══════════════════════════════════════════════════════
#  Learning Core — 学习核心
# ══════════════════════════════════════════════════════


# ── LearningTask ──────────────────────────────────────


class LearningTaskCreate(OrmBase):
    """创建学习任务"""

    student_id: UUID
    knowledge_point_id: UUID
    task_type: str = Field(default="exercise", description="exercise|reading|review")
    source_resource_id: Optional[UUID] = None
    due_date: Optional[datetime] = None


class LearningTaskUpdate(OrmBase):
    """更新学习任务"""

    status: Optional[str] = None
    score: Optional[int] = None
    answer_snapshot: Optional[dict] = None


class LearningTaskOut(OrmBase):
    """学习任务响应"""

    id: UUID
    student_id: UUID
    knowledge_point_id: UUID
    task_type: str
    status: str
    source_resource_id: Optional[UUID]
    score: Optional[int]
    answer_snapshot: Optional[dict]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ── MasteryRecord ─────────────────────────────────────


class MasteryRecordOut(OrmBase):
    """掌握度记录"""

    id: UUID
    student_id: UUID
    knowledge_point_id: UUID
    mastery_level: float
    attempt_count: int
    last_attempt_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ── StudySession ──────────────────────────────────────


class StudySessionCreate(OrmBase):
    """创建学习会话"""

    student_id: UUID
    knowledge_point_id: Optional[UUID] = None
    session_type: str = "exercise"


class StudySessionOut(OrmBase):
    """学习会话响应"""

    id: UUID
    student_id: UUID
    knowledge_point_id: Optional[UUID]
    session_type: str
    duration_seconds: int
    events: Optional[list]
    created_at: datetime
    updated_at: datetime