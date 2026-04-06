"""
学习编排 业务逻辑
──────────────────
任务编排 + 进度追踪（管理员视角为主）
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.persistence.models import Task, TaskItem, TaskProgress
from infrastructure.persistence.models.base import generate_uuid7
from shared.exceptions import NotFoundError, BusinessError

logger = structlog.get_logger()


class LearningService:
    """学习任务编排服务（管理员侧）"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 任务 CRUD ─────────────────────────────────────

    async def create_task(self, data, created_by: str) -> Task:
        """创建学习任务（含子项）

        data: dict 或 Pydantic model (TaskCreate)
        """
        if hasattr(data, "model_dump"):
            data = data.model_dump(exclude_unset=True)
        else:
            data = dict(data)  # 确保可变
        items_data = data.pop("items", [])

        task = Task(
            id=str(generate_uuid7()),
            created_by=created_by,
            **data,
        )
        self.db.add(task)

        # 创建子任务项
        for idx, item_data in enumerate(items_data):
            item = TaskItem(
                id=str(generate_uuid7()),
                task_id=task.id,
                sort_order=item_data.pop("sort_order", idx),
                **item_data,
            )
            self.db.add(item)

        await self.db.flush()
        # 带关联重新加载
        return await self._load_task_detail(str(task.id))

    async def get_task(self, task_id: str) -> Task:
        """获取任务基本信息"""
        stmt = select(Task).where(
            Task.id == task_id,
            Task.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("task", task_id)
        return task

    async def get_task_detail(self, task_id: str) -> Task:
        """获取任务详情（含子项）"""
        return await self._load_task_detail(task_id)

    async def list_tasks(
        self,
        status: Optional[str] = None,
        subject: Optional[str] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        """任务列表（管理员视角）"""
        base = select(Task).where(Task.deleted_at.is_(None))
        if status:
            base = base.where(Task.status == status)
        if subject:
            base = base.where(Task.subject == subject)
        if created_by:
            base = base.where(Task.created_by == created_by)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def list_tasks_for_student(
        self, student_id: str, status: str | None = None,
        page: int = 1, page_size: int = 20
    ):
        """学生端查询自己的任务列表（适配路由调用）"""
        return await self.list_tasks(
            status=status, subject=None,
            created_by=student_id, page=page, page_size=page_size,
        )

    async def update_task(self, task_id: str, data=None, **kwargs) -> Task:
        """更新任务

        data: Pydantic model (TaskUpdate) 或 dict 或 None
        也支持直接传关键字参数 (向后兼容)
        """
        task = await self.get_task(task_id)
        updates = kwargs
        if data is not None:
            if hasattr(data, "model_dump"):
                updates = data.model_dump(exclude_unset=True)
            elif isinstance(data, dict):
                updates = data
        for k, v in updates.items():
            if v is not None and hasattr(task, k):
                setattr(task, k, v)
        await self.db.flush()
        await self.db.refresh(task)
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
            raise BusinessError(f"只有草稿状态可以发布，当前: {task.status}")
        task.status = "published"
        task.publish_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(task)
        logger.info("task_published", task_id=task_id)
        return task

    async def archive_task(self, task_id: str) -> Task:
        """归档任务"""
        task = await self.get_task(task_id)
        task.status = "archived"
        await self.db.flush()
        await self.db.refresh(task)
        logger.info("task_archived", task_id=task_id)
        return task

    async def delete_task(self, task_id: str) -> Task:
        """软删除"""
        task = await self.get_task(task_id)
        task.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(task)
        logger.info("task_soft_deleted", task_id=task_id)
        return task

    # ── 子项管理 ──────────────────────────────────────

    async def list_items(self, task_id: str) -> list[TaskItem]:
        """获取任务下所有子项"""
        await self.get_task(task_id)  # 确保任务存在
        stmt = (
            select(TaskItem)
            .where(TaskItem.task_id == task_id, TaskItem.deleted_at.is_(None))
            .order_by(TaskItem.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_item(self, task_id: str, data) -> TaskItem:
        """向任务添加子项"""
        await self.get_task(task_id)  # 确保任务存在
        if hasattr(data, "model_dump"):
            item_data = data.model_dump(exclude_unset=True)
        else:
            item_data = dict(data)
        item = TaskItem(
            id=str(generate_uuid7()),
            task_id=task_id,
            **item_data,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        logger.info("task_item_added", task_id=task_id, item_id=str(item.id))
        return item

    async def update_item(self, task_id: str, item_id: str, data) -> TaskItem:
        """更新子项"""
        await self.get_task(task_id)  # 确保任务存在
        stmt = select(TaskItem).where(
            TaskItem.id == item_id,
            TaskItem.task_id == task_id,
            TaskItem.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("task_item", item_id)
        updates = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else dict(data)
        for k, v in updates.items():
            if hasattr(item, k):
                setattr(item, k, v)
        await self.db.flush()
        await self.db.refresh(item)
        logger.info("task_item_updated", task_id=task_id, item_id=item_id)
        return item

    async def delete_item(self, task_id: str, item_id: str) -> None:
        """软删除子项"""
        await self.get_task(task_id)  # 确保任务存在
        stmt = select(TaskItem).where(
            TaskItem.id == item_id,
            TaskItem.task_id == task_id,
            TaskItem.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("task_item", item_id)
        item.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("task_item_deleted", task_id=task_id, item_id=item_id)

    # ── 进度 ──────────────────────────────────────────

    async def start_progress(self, task_id: str, student_id: str) -> TaskProgress:
        """开始任务进度 — 创建或返回 in_progress 进度记录"""
        task = await self.get_task(task_id)

        # 检查是否已有进度记录
        stmt = select(TaskProgress).where(
            TaskProgress.task_id == task_id,
            TaskProgress.student_id == student_id,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        progress = TaskProgress(
            id=generate_uuid7(),
            task_id=task_id,
            student_id=student_id,
            status="in_progress",
            started_at=func.now(),
            item_progress={},
        )
        self.db.add(progress)
        await self.db.flush()
        await self.db.refresh(progress)
        logger.info("progress_started", task_id=task_id, student_id=student_id)
        return progress

    async def submit_progress(
        self, task_id: str, student_id: str, data=None
    ) -> TaskProgress:
        """学生提交进度

        路由调用: submit_progress(task_id, student_id=..., data=body)
          body: ProgressSubmit(answers=[], time_spent=0)
        """
        # 查找或创建进度记录
        stmt = select(TaskProgress).where(
            TaskProgress.task_id == task_id,
            TaskProgress.student_id == student_id,
        )
        progress = (await self.db.execute(stmt)).scalar_one_or_none()
        if not progress:
            raise NotFoundError("task_progress", task_id)

        answers = []
        time_spent = 0
        if data is not None:
            answers = getattr(data, "answers", []) or []
            time_spent = getattr(data, "time_spent", 0) or 0

        # 计算总分
        total_score = 0
        if answers:
            total_score = sum(a.get("score", 0) for a in answers if isinstance(a, dict))

        progress.status = "completed"
        progress.score = total_score
        progress.completed_at = func.now()
        progress.item_progress = {
            "answers": answers,
            "time_spent": time_spent,
        }

        await self.db.flush()
        await self.db.refresh(progress)

        logger.info(
            "progress_submitted",
            task_id=task_id,
            student_id=student_id,
            score=total_score,
        )
        return progress

    async def get_task_progress(
        self, task_id: str, student_id: str
    ) -> TaskProgress | None:
        """获取学生在某任务下的进度"""
        stmt = select(TaskProgress).where(
            TaskProgress.task_id == task_id,
            TaskProgress.student_id == student_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_task_progress(
        self, task_id: str, page: int = 1, page_size: int = 20,
    ) -> tuple[list[TaskProgress], int]:
        """管理员视角 — 获取任务下所有学生的进度"""
        await self.get_task(task_id)  # 确保任务存在
        base = select(TaskProgress).where(TaskProgress.task_id == task_id)
        # count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        # list
        stmt = base.order_by(TaskProgress.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    # ── private ───────────────────────────────────────

    async def _load_task_detail(self, task_id: str) -> Task:
        stmt = (
            select(Task)
            .options(selectinload(Task.items))
            .where(Task.id == task_id, Task.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("task", task_id)
        return task
