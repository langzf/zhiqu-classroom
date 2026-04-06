"""
内容引擎 业务逻辑
──────────────────
教材 / 章节 / 知识点 CRUD 与向量搜索
"""

from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models import (
    Chapter,
    KnowledgePoint,
    KpEmbedding,
    Textbook,
)
from infrastructure.persistence.models.base import generate_uuid7
from shared.exceptions import NotFoundError

logger = structlog.get_logger()


class ContentService:
    """内容引擎核心服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 教材 ──────────────────────────────────────────

    async def create_textbook(self, data: dict) -> Textbook:
        tb = Textbook(id=str(generate_uuid7()), **data)
        self.db.add(tb)
        await self.db.flush()
        await self.db.refresh(tb)
        logger.info("textbook_created", textbook_id=str(tb.id), title=tb.title)
        return tb

    async def get_textbook(self, textbook_id: str) -> Textbook:
        stmt = select(Textbook).where(
            Textbook.id == textbook_id,
            Textbook.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        tb = result.scalar_one_or_none()
        if not tb:
            raise NotFoundError("textbook", textbook_id)
        return tb

    async def get_textbook_detail(self, textbook_id: str) -> dict:
        """获取教材详情（含章节树）"""
        textbook = await self.get_textbook(textbook_id)
        chapters = await self.get_chapter_tree(textbook_id)
        result = {
            "id": str(textbook.id),
            "title": textbook.title,
            "subject": textbook.subject,
            "grade_range": textbook.grade_range,
            "cover_url": textbook.cover_url,
            "source_file_url": textbook.source_file_url,
            "parse_status": textbook.parse_status,
            "created_at": textbook.created_at,
            "updated_at": textbook.updated_at,
            "chapters": chapters,
        }
        return result

    async def list_textbooks(
        self,
        subject: Optional[str] = None,
        grade_range: Optional[str] = None,
        parse_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Textbook], int]:
        base = select(Textbook).where(Textbook.deleted_at.is_(None))
        if subject:
            base = base.where(Textbook.subject == subject)
        if grade_range:
            base = base.where(Textbook.grade_range == grade_range)
        if parse_status:
            base = base.where(Textbook.parse_status == parse_status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(Textbook.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def update_textbook(self, textbook_id: str, **kwargs) -> Textbook:
        tb = await self.get_textbook(textbook_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(tb, k):
                setattr(tb, k, v)
        await self.db.flush()
        await self.db.refresh(tb)
        logger.info(
            "textbook_updated",
            textbook_id=textbook_id,
            fields=list(kwargs.keys()),
        )
        return tb

    async def delete_textbook(self, textbook_id: str) -> Textbook:
        from datetime import datetime, timezone

        tb = await self.get_textbook(textbook_id)
        tb.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(tb)
        logger.info("textbook_soft_deleted", textbook_id=textbook_id)
        return tb

    async def parse_textbook(self, textbook_id: str) -> dict:
        """触发教材解析（MVP 阶段为 stub）"""
        tb = await self.get_textbook(textbook_id)
        tb.parse_status = "parsing"
        await self.db.flush()
        await self.db.refresh(tb)
        logger.info("textbook_parse_triggered", textbook_id=textbook_id)
        return {"textbook_id": str(tb.id), "parse_status": tb.parse_status}

    async def generate_resource(self, data) -> dict:
        """生成教学资源（MVP 阶段为 stub）"""
        logger.info("generate_resource_stub", data=str(data))
        return {"status": "queued", "message": "Resource generation is not yet implemented"}

    # ── 章节 ──────────────────────────────────────────

    async def get_chapter_tree(self, textbook_id: str) -> list[Chapter]:
        """获取教材的章节树（一次性加载全部，前端构建树）"""
        await self.get_textbook(textbook_id)  # 确认教材存在
        stmt = (
            select(Chapter)
            .where(
                Chapter.textbook_id == textbook_id,
                Chapter.deleted_at.is_(None),
            )
            .order_by(Chapter.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_chapter(self, chapter_id: str) -> Chapter:
        stmt = select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        ch = result.scalar_one_or_none()
        if not ch:
            raise NotFoundError("chapter", chapter_id)
        return ch

    # ── 知识点 ────────────────────────────────────────

    async def list_knowledge_points(
        self,
        chapter_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[KnowledgePoint], int]:
        base = select(KnowledgePoint).where(
            KnowledgePoint.chapter_id == chapter_id,
            KnowledgePoint.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(KnowledgePoint.sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def get_knowledge_point(self, kp_id: str) -> KnowledgePoint:
        stmt = select(KnowledgePoint).where(
            KnowledgePoint.id == kp_id,
            KnowledgePoint.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        kp = result.scalar_one_or_none()
        if not kp:
            raise NotFoundError("knowledge_point", kp_id)
        return kp

    async def create_knowledge_point(self, data: dict) -> KnowledgePoint:
        kp = KnowledgePoint(id=str(generate_uuid7()), **data)
        self.db.add(kp)
        await self.db.flush()
        await self.db.refresh(kp)
        logger.info(
            "knowledge_point_created",
            kp_id=str(kp.id),
            chapter_id=kp.chapter_id,
        )
        return kp

    # ── 向量搜索 ──────────────────────────────────────

    async def search_knowledge_points(
        self,
        query_embedding: list[float],
        subject: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[dict]:
        """向量相似度搜索知识点"""
        from pgvector.sqlalchemy import Vector

        # cosine distance
        distance = KpEmbedding.embedding.cosine_distance(query_embedding)

        stmt = (
            select(
                KpEmbedding.knowledge_point_id,
                KpEmbedding.chunk_text,
                distance.label("distance"),
            )
            .where(distance < (1 - threshold))
            .order_by(distance)
            .limit(limit)
        )

        # 可选按 subject 过滤（需要 join knowledge_points → chapters → textbooks）
        if subject:
            stmt = (
                stmt.join(
                    KnowledgePoint,
                    KpEmbedding.knowledge_point_id == KnowledgePoint.id,
                )
                .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
                .join(Textbook, Chapter.textbook_id == Textbook.id)
                .where(Textbook.subject == subject)
            )

        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "knowledge_point_id": str(row.knowledge_point_id),
                "chunk_text": row.chunk_text,
                "similarity": round(1 - row.distance, 4),
            }
            for row in rows
        ]

    async def search_knowledge_points_by_query(self, body) -> list[dict]:
        """文本模糊搜索知识点（MVP fallback，后续升级为向量搜索）"""
        query = getattr(body, "query", "") or ""
        subject = getattr(body, "subject", None)
        limit = getattr(body, "limit", 10) or 10

        stmt = (
            select(KnowledgePoint)
            .where(
                KnowledgePoint.deleted_at.is_(None),
                KnowledgePoint.name.ilike(f"%{query}%"),
            )
        )

        if subject:
            stmt = (
                stmt.join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
                .join(Textbook, Chapter.textbook_id == Textbook.id)
                .where(Textbook.subject == subject)
            )

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": str(kp.id),
                "name": kp.name,
                "chapter_id": str(kp.chapter_id),
                "difficulty": kp.difficulty,
            }
            for kp in rows
        ]

    # ── 生成资源查询 ──────────────────────────────────

    async def list_resources(
        self,
        knowledge_point_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        """查询已生成资源列表"""
        base = select(GeneratedResource).where(
            GeneratedResource.deleted_at.is_(None)
        )
        if knowledge_point_id:
            base = base.where(
                GeneratedResource.knowledge_point_id == knowledge_point_id
            )
        if resource_type:
            base = base.where(GeneratedResource.resource_type == resource_type)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = (
            base.order_by(GeneratedResource.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    # ── 上传目录 ──────────────────────────────────────

    async def upload_toc(self, textbook_id: str, chapters: list[dict]) -> list:
        """批量创建/替换教材章节目录

        chapters: [{title, sort_order, parent_id?, children?}]
        """
        textbook = await self.get_textbook(textbook_id)
        if not textbook:
            raise NotFoundError("textbook", textbook_id)

        created = []

        async def _create_chapter(data: dict, parent_id=None):
            children_data = data.pop("children", [])
            chapter = Chapter(
                id=str(generate_uuid7()),
                textbook_id=textbook_id,
                parent_id=parent_id,
                title=data.get("title", ""),
                sort_order=data.get("sort_order", 0),
            )
            self.db.add(chapter)
            await self.db.flush()
            created.append(chapter)
            for child in children_data:
                await _create_chapter(child, parent_id=str(chapter.id))

        for ch in chapters:
            await _create_chapter(ch)

        await self.db.flush()
        logger.info(
            "toc_uploaded",
            textbook_id=textbook_id,
            chapter_count=len(created),
        )
        return created
