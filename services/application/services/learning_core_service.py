"""
学习核心服务
─────────────────────
学习任务 CRUD、掌握度更新、学习会话记录。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import NotFoundError, ValidationError

from infrastructure.persistence.models.learning import (
    LearningTask,
    MasteryRecord,
    StudySession,
)

logger = structlog.get_logger(__name__)

TASK_STATUSES = ("pending", "in_progress", "completed", "expired")
TASK_TYPES = ("exercise", "reading", "review")


class LearningCoreService:
    """学习核心服务（学生侧学习任务、掌握度、会话）"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── LearningTask ──────────────────────────────────

    async def create_task(
        self,
        student_id: str,
        knowledge_point_id: str,
        task_type: str = "exercise",
        source_resource_id: Optional[str] = None,
        due_date: Optional[datetime] = None,
    ) -> LearningTask:
        if task_type not in TASK_TYPES:
            raise ValidationError(f"Invalid task_type: {task_type}")

        task = LearningTask(
            student_id=student_id,
            knowledge_point_id=knowledge_point_id,
            task_type=task_type,
            source_resource_id=source_resource_id,
            due_date=due_date,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: str) -> LearningTask:
        stmt = select(LearningTask).where(
            LearningTask.id == task_id,
            LearningTask.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("学习任务不存在")
        return task

    async def list_tasks(
        self,
        student_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LearningTask], int]:
        base = select(LearningTask).where(
            LearningTask.student_id == student_id,
            LearningTask.deleted_at.is_(None),
        )
        if status:
            base = base.where(LearningTask.status == status)
        if task_type:
            base = base.where(LearningTask.task_type == task_type)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(LearningTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.db.execute(items_stmt)).scalars().all())
        return items, total

    async def update_task(self, task_id: str, **kwargs) -> LearningTask:
        task = await self.get_task(task_id)

        # 状态流转校验
        new_status = kwargs.get("status")
        if new_status:
            if new_status not in TASK_STATUSES:
                raise ValidationError(f"Invalid status: {new_status}")
            if task.status == "completed":
                raise ValidationError("已完成任务不可修改状态")

        for k, v in kwargs.items():
            if hasattr(task, k):
                setattr(task, k, v)

        # 自动设置完成时间
        if new_status == "completed" and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def submit_task(
        self,
        task_id: str,
        score: int,
        answer_snapshot: Optional[dict] = None,
    ) -> LearningTask:
        """学生提交任务答案"""
        task = await self.get_task(task_id)
        if task.status == "completed":
            raise ValidationError("任务已完成")

        task.status = "completed"
        task.score = max(0, min(100, score))
        task.answer_snapshot = answer_snapshot
        task.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(task)

        # 更新掌握度
        await self._update_mastery(
            student_id=task.student_id,
            knowledge_point_id=task.knowledge_point_id,
            score=task.score,
        )

        return task

    # ── MasteryRecord ─────────────────────────────────

    async def get_mastery(
        self, student_id: str, knowledge_point_id: str
    ) -> Optional[MasteryRecord]:
        stmt = select(MasteryRecord).where(
            MasteryRecord.student_id == student_id,
            MasteryRecord.knowledge_point_id == knowledge_point_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_mastery(
        self,
        student_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[MasteryRecord], int]:
        base = select(MasteryRecord).where(
            MasteryRecord.student_id == student_id,
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(MasteryRecord.mastery_level.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.db.execute(items_stmt)).scalars().all())
        return items, total

    async def _update_mastery(
        self,
        student_id: str,
        knowledge_point_id: str,
        score: int,
    ):
        """根据任务得分更新掌握度（简单加权平均）"""
        record = await self.get_mastery(student_id, knowledge_point_id)
        new_level = score / 100.0

        if record:
            # 加权平均：历史占 0.7，新得分占 0.3
            record.mastery_level = round(
                record.mastery_level * 0.7 + new_level * 0.3, 4
            )
            record.attempt_count += 1
            record.last_attempt_at = datetime.now(timezone.utc)
        else:
            record = MasteryRecord(
                student_id=student_id,
                knowledge_point_id=knowledge_point_id,
                mastery_level=round(new_level, 4),
                attempt_count=1,
                last_attempt_at=datetime.now(timezone.utc),
            )
            self.db.add(record)

        await self.db.flush()
        await self.db.refresh(record)
        return record

    # ── StudySession ──────────────────────────────────

    async def create_study_session(
        self,
        student_id: str,
        knowledge_point_id: Optional[str] = None,
        session_type: str = "exercise",
    ) -> StudySession:
        session = StudySession(
            student_id=student_id,
            knowledge_point_id=knowledge_point_id,
            session_type=session_type,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update_study_session(
        self,
        session_id: str,
        duration_seconds: Optional[int] = None,
        events: Optional[list] = None,
    ) -> StudySession:
        stmt = select(StudySession).where(StudySession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("学习会话不存在")

        if duration_seconds is not None:
            session.duration_seconds = duration_seconds
        if events is not None:
            session.events = events

        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def list_study_sessions(
        self,
        student_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StudySession], int]:
        base = select(StudySession).where(
            StudySession.student_id == student_id,
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(StudySession.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.db.execute(items_stmt)).scalars().all())
        return items, total

    # ── 统计 ──────────────────────────────────────────

    async def get_student_progress(self, student_id: str) -> dict:
        """获取学生学习进度概览"""
        # 任务统计
        task_base = select(LearningTask).where(
            LearningTask.student_id == student_id,
            LearningTask.deleted_at.is_(None),
        )

        total_tasks = (
            await self.db.execute(
                select(func.count()).select_from(task_base.subquery())
            )
        ).scalar() or 0

        completed_tasks = (
            await self.db.execute(
                select(func.count()).select_from(
                    task_base.where(LearningTask.status == "completed").subquery()
                )
            )
        ).scalar() or 0

        avg_score = (
            await self.db.execute(
                select(func.avg(LearningTask.score)).where(
                    LearningTask.student_id == student_id,
                    LearningTask.status == "completed",
                    LearningTask.deleted_at.is_(None),
                )
            )
        ).scalar()

        # 掌握度统计
        mastery_count = (
            await self.db.execute(
                select(func.count()).where(
                    MasteryRecord.student_id == student_id,
                )
            )
        ).scalar() or 0

        avg_mastery = (
            await self.db.execute(
                select(func.avg(MasteryRecord.mastery_level)).where(
                    MasteryRecord.student_id == student_id,
                )
            )
        ).scalar()

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": round(completed_tasks / total_tasks, 4) if total_tasks else 0,
            "avg_score": round(float(avg_score), 1) if avg_score else None,
            "knowledge_points_touched": mastery_count,
            "avg_mastery": round(float(avg_mastery), 4) if avg_mastery else None,
        }
