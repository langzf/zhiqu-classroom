"""Learning Core Schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from shared.schemas import OrmBase


# ── LearningTask ──


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


# ── MasteryRecord ──


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


# ── StudySession ──


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
