"""
learning_orchestrator 业务逻辑
──────────────────────────────
学习任务管理 + 学生进度跟踪
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from learning_orchestrator.models import Task, TaskItem, TaskProgress
from shared.base_model import generate_uuid7
from shared.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


class LearningService:
    """学习编排核心服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 任务管理（admin）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def create_task(
        self,
        created_by: str,
        title: str,
        description: Optional[str] = None,
        task_type: str = "homework",
        subject: Optional[str] = None,
        grade_range: Optional[str] = None,
        publish_at: Optional[datetime] = None,
        deadline: Optional[datetime] = None,
        config: Optional[dict] = None,
        items: Optional[list[dict]] = None,
    ) -> Task:
        """创建学习任务（含子项）"""
        task = Task(
            id=str(generate_uuid7()),
            title=title,
            description=description,
            task_type=task_type,
            status="draft",
            created_by=created_by,
            subject=subject,
            grade_range=grade_range,
            publish_at=publish_at,
            deadline=deadline,
            config=config,
        )
        self.db.add(task)

        # 批量创建子项
        if items:
            for idx, item_data in enumerate(items):
                task_item = TaskItem(
                    id=str(generate_uuid7()),
                    task_id=task.id,
                    item_type=item_data["item_type"],
                    resource_id=item_data.get("resource_id"),
                    knowledge_point_id=item_data.get("knowledge_point_id"),
                    title=item_data["title"],
                    config=item_data.get("config"),
                    sort_order=item_data.get("sort_order", idx),
                )
                self.db.add(task_item)

        await self.db.flush()
        logger.info(
            "task_created",
            task_id=str(task.id),
            created_by=created_by,
            item_count=len(items) if items else 0,
        )
        return task

    async def get_task(self, task_id: str) -> Task:
        """获取任务（含子项）"""
        stmt = select(Task).where(
            Task.id == task_id,
            Task.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("task", task_id)
        return task

    async def list_tasks(
        self,
        status: Optional[str] = None,
        subject: Optional[str] = None,
        task_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        """任务列表（分页 + 筛选）"""
        base = select(Task).where(Task.deleted_at.is_(None))

        if status:
            base = base.where(Task.status == status)
        if subject:
            base = base.where(Task.subject == subject)
        if task_type:
            base = base.where(Task.task_type == task_type)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def update_task(self, task_id: str, **kwargs) -> Task:
        """更新任务字段"""
        task = await self.get_task(task_id)
        for k, v in kwargs.items():
            if hasattr(task, k):
                setattr(task, k, v)
        await self.db.flush()
        logger.info(
            "task_updated",
            task_id=task_id,
            fields=list(kwargs.keys()),
        )
        return task

    async def publish_task(self, task_id: str) -> Task:
        """发布任务"""
        task = await self.get_task(task_id)
        if task.status != "draft":
            raise ValidationError(f"只有 draft 状态的任务可以发布，当前: {task.status}")
        task.status = "published"
        await self.db.flush()
        logger.info("task_published", task_id=task_id)
        return task

    async def archive_task(self, task_id: str) -> Task:
        """归档任务"""
        return await self.update_task(task_id, status="archived")

    async def soft_delete_task(self, task_id: str) -> Task:
        """软删除任务"""
        task = await self.get_task(task_id)
        task.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("task_soft_deleted", task_id=task_id)
        return task

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 任务子项管理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def add_task_item(self, task_id: str, item_data: dict) -> TaskItem:
        """给任务添加子项"""
        await self.get_task(task_id)  # 确认任务存在
        item = TaskItem(
            id=str(generate_uuid7()),
            task_id=task_id,
            item_type=item_data["item_type"],
            resource_id=item_data.get("resource_id"),
            knowledge_point_id=item_data.get("knowledge_point_id"),
            title=item_data["title"],
            config=item_data.get("config"),
            sort_order=item_data.get("sort_order", 0),
        )
        self.db.add(item)
        await self.db.flush()
        logger.info("task_item_added", task_id=task_id, item_id=str(item.id))
        return item

    async def remove_task_item(self, item_id: str) -> None:
        """删除任务子项（硬删除）"""
        stmt = select(TaskItem).where(TaskItem.id == item_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("task_item", item_id)
        await self.db.delete(item)
        await self.db.flush()
        logger.info("task_item_removed", item_id=item_id)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 学生进度
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def start_task(self, task_id: str, student_id: str) -> TaskProgress:
        """学生开始任务"""
        task = await self.get_task(task_id)
        if task.status != "published":
            raise ValidationError("任务未发布，无法开始")

        # 检查是否已有进度
        stmt = select(TaskProgress).where(
            TaskProgress.task_id == task_id,
            TaskProgress.student_id == student_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing  # 幂等，已开始则直接返回

        progress = TaskProgress(
            id=str(generate_uuid7()),
            task_id=task_id,
            student_id=student_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(progress)
        await self.db.flush()
        logger.info(
            "task_started",
            task_id=task_id,
            student_id=student_id,
        )
        return progress

    async def submit_task(
        self,
        task_id: str,
        student_id: str,
        item_results: Optional[list[dict]] = None,
    ) -> TaskProgress:
        """学生提交任务完成"""
        stmt = select(TaskProgress).where(
            TaskProgress.task_id == task_id,
            TaskProgress.student_id == student_id,
        )
        result = await self.db.execute(stmt)
        progress = result.scalar_one_or_none()
        if not progress:
            raise NotFoundError("task_progress", f"task={task_id}, student={student_id}")

        if progress.status == "completed":
            raise ValidationError("任务已完成，不可重复提交")

        # 处理子项结果
        item_progress = {}
        total_score = 0
        score_count = 0
        if item_results:
            for ir in item_results:
                item_id = ir["item_id"]
                item_progress[item_id] = {
                    "status": "completed",
                    "score": ir.get("score"),
                    "answer_data": ir.get("answer_data"),
                }
                if ir.get("score") is not None:
                    total_score += ir["score"]
                    score_count += 1

        progress.status = "completed"
        progress.completed_at = datetime.now(timezone.utc)
        progress.item_progress = item_progress
        if score_count > 0:
            progress.score = total_score // score_count

        await self.db.flush()
        logger.info(
            "task_submitted",
            task_id=task_id,
            student_id=student_id,
            score=progress.score,
        )
        return progress

    async def get_progress(self, task_id: str, student_id: str) -> TaskProgress:
        """获取学生的任务进度"""
        stmt = select(TaskProgress).where(
            TaskProgress.task_id == task_id,
            TaskProgress.student_id == student_id,
        )
        result = await self.db.execute(stmt)
        progress = result.scalar_one_or_none()
        if not progress:
            raise NotFoundError("task_progress", f"task={task_id}, student={student_id}")
        return progress

    async def list_student_progress(
        self,
        student_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TaskProgress], int]:
        """学生的所有任务进度（分页）"""
        base = select(TaskProgress).where(TaskProgress.student_id == student_id)
        if status:
            base = base.where(TaskProgress.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(TaskProgress.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total
