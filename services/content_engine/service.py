"""content_engine 业务逻辑"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.base_model import generate_uuid7
from shared.exceptions import NotFoundError
from content_engine.models import (
    Chapter,
    GeneratedResource,
    KnowledgePoint,
    KpEmbedding,
    PromptTemplate,
    Textbook,
)

logger = structlog.get_logger()


class ContentService:
    """内容引擎业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 教材 ──────────────────────────────────────────

    async def create_textbook(
        self,
        title: str,
        subject: str,
        grade_range: str,
        source_file_url: str,
    ) -> Textbook:
        textbook = Textbook(
            id=generate_uuid7(),
            title=title,
            subject=subject,
            grade_range=grade_range,
            source_file_url=source_file_url,
            parse_status="pending",
        )
        self.db.add(textbook)
        await self.db.flush()
        logger.info("textbook_created", textbook_id=str(textbook.id), title=title)
        return textbook

    async def get_textbook(self, textbook_id: str) -> Textbook:
        stmt = select(Textbook).where(
            Textbook.id == textbook_id, Textbook.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        tb = result.scalar_one_or_none()
        if not tb:
            raise NotFoundError("textbook", textbook_id)
        return tb

    async def list_textbooks(
        self,
        subject: Optional[str] = None,
        grade_range: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Textbook], int]:
        stmt = select(Textbook).where(Textbook.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Textbook).where(
            Textbook.deleted_at.is_(None)
        )

        if subject:
            stmt = stmt.where(Textbook.subject == subject)
            count_stmt = count_stmt.where(Textbook.subject == subject)
        if grade_range:
            stmt = stmt.where(Textbook.grade_range == grade_range)
            count_stmt = count_stmt.where(Textbook.grade_range == grade_range)

        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(Textbook.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def update_parse_status(
        self, textbook_id: str, status: str
    ) -> Textbook:
        tb = await self.get_textbook(textbook_id)
        tb.parse_status = status
        await self.db.flush()
        logger.info(
            "textbook_parse_status_updated",
            textbook_id=str(tb.id),
            status=status,
        )
        return tb

    async def soft_delete_textbook(self, textbook_id: str) -> Textbook:
        """软删除教材"""
        tb = await self.get_textbook(textbook_id)
        tb.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("textbook_soft_deleted", textbook_id=str(tb.id))
        return tb

    # ── 章节 ──────────────────────────────────────────

    async def create_chapter(
        self,
        textbook_id: str,
        title: str,
        parent_id: Optional[str] = None,
        depth: int = 1,
        sort_order: int = 0,
        content_text: Optional[str] = None,
    ) -> Chapter:
        chapter = Chapter(
            id=generate_uuid7(),
            textbook_id=textbook_id,
            parent_id=parent_id,
            title=title,
            depth=depth,
            sort_order=sort_order,
            content_text=content_text,
        )
        self.db.add(chapter)
        await self.db.flush()
        return chapter

    async def get_chapter_tree(self, textbook_id: str) -> list[Chapter]:
        """获取教材的章节树（平铺，由调用方组装树结构）"""
        stmt = (
            select(Chapter)
            .where(Chapter.textbook_id == textbook_id)
            .order_by(Chapter.depth, Chapter.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── 知识点 ────────────────────────────────────────

    async def create_knowledge_point(
        self,
        chapter_id: str,
        title: str,
        description: Optional[str] = None,
        difficulty: int = 3,
        bloom_level: Optional[str] = None,
        tags: Optional[dict] = None,
    ) -> KnowledgePoint:
        kp = KnowledgePoint(
            id=generate_uuid7(),
            chapter_id=chapter_id,
            title=title,
            description=description,
            difficulty=difficulty,
            bloom_level=bloom_level,
            tags=tags,
        )
        self.db.add(kp)
        await self.db.flush()
        return kp

    async def list_knowledge_points(
        self, chapter_id: str
    ) -> list[KnowledgePoint]:
        stmt = (
            select(KnowledgePoint)
            .where(KnowledgePoint.chapter_id == chapter_id)
            .order_by(KnowledgePoint.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_knowledge_point(self, kp_id: str) -> KnowledgePoint:
        """获取单个知识点详情"""
        stmt = select(KnowledgePoint).where(KnowledgePoint.id == kp_id)
        result = await self.db.execute(stmt)
        kp = result.scalar_one_or_none()
        if not kp:
            raise NotFoundError("knowledge_point", kp_id)
        return kp

    # ── 向量 ──────────────────────────────────────────

    async def store_embedding(
        self,
        kp_id: str,
        model_name: str,
        embedding: list[float],
        source_text: Optional[str] = None,
    ) -> KpEmbedding:
        kpe = KpEmbedding(
            id=generate_uuid7(),
            knowledge_point_id=kp_id,
            model_name=model_name,
            embedding=embedding,
            source_text=source_text,
        )
        self.db.add(kpe)
        await self.db.flush()
        return kpe

    async def search_similar_kp(
        self,
        query_embedding: list[float],
        limit: int = 10,
        model_name: Optional[str] = None,
    ) -> list[dict]:
        """向量相似度搜索知识点"""
        from sqlalchemy import text

        model_filter = ""
        params: dict = {"embedding": str(query_embedding), "limit": limit}
        if model_name:
            model_filter = "AND model_name = :model_name"
            params["model_name"] = model_name

        sql = text(f"""
            SELECT kpe.knowledge_point_id,
                   kp.title,
                   kp.description,
                   kpe.source_text,
                   kpe.embedding <=> :embedding::vector AS distance
            FROM content.kp_embeddings kpe
            JOIN content.knowledge_points kp ON kp.id = kpe.knowledge_point_id
            WHERE 1=1 {model_filter}
            ORDER BY distance
            LIMIT :limit
        """)
        result = await self.db.execute(sql, params)
        rows = result.fetchall()
        return [
            {
                "knowledge_point_id": str(r[0]),
                "title": r[1],
                "description": r[2],
                "source_text": r[3],
                "distance": float(r[4]),
            }
            for r in rows
        ]

    # ── 生成资源 ──────────────────────────────────────

    async def save_generated_resource(
        self,
        kp_id: str,
        resource_type: str,
        title: str,
        content_json: dict,
        prompt_template_id: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> GeneratedResource:
        gr = GeneratedResource(
            id=generate_uuid7(),
            knowledge_point_id=kp_id,
            resource_type=resource_type,
            title=title,
            content_json=content_json,
            prompt_template_id=prompt_template_id,
            llm_model=llm_model,
        )
        self.db.add(gr)
        await self.db.flush()
        logger.info(
            "resource_generated",
            kp_id=kp_id,
            resource_type=resource_type,
        )
        return gr

    async def list_generated_resources(
        self,
        kp_id: str,
        resource_type: Optional[str] = None,
    ) -> list[GeneratedResource]:
        stmt = select(GeneratedResource).where(
            GeneratedResource.knowledge_point_id == kp_id
        )
        if resource_type:
            stmt = stmt.where(GeneratedResource.resource_type == resource_type)
        stmt = stmt.order_by(GeneratedResource.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Prompt 模板 ───────────────────────────────────

    async def get_active_template(self, resource_type: str) -> Optional[PromptTemplate]:
        stmt = (
            select(PromptTemplate)
            .where(
                PromptTemplate.resource_type == resource_type,
                PromptTemplate.is_active.is_(True),
                PromptTemplate.deleted_at.is_(None),
            )
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── 文件上传 + 教材创建 ──────────────────────────

    async def upload_and_create_textbook(
        self,
        *,
        title: str,
        subject: str,
        grade_range: str,
        filename: str,
        file_data: bytes,
        content_type: str,
    ) -> Textbook:
        """上传文件到 MinIO，创建教材记录。"""
        from shared.minio_client import upload_file

        textbook_id = str(generate_uuid7())
        object_name = f"textbooks/{textbook_id}/{filename}"

        # 上传到 MinIO
        await upload_file(object_name, file_data, content_type)
        logger.info(
            "textbook_file_uploaded",
            textbook_id=textbook_id,
            object_name=object_name,
            size=len(file_data),
        )

        # 创建数据库记录
        textbook = Textbook(
            id=textbook_id,
            title=title,
            subject=subject,
            grade_range=grade_range,
            source_file_url=object_name,
            parse_status="pending",
        )
        self.db.add(textbook)
        await self.db.flush()
        logger.info("textbook_created", textbook_id=textbook_id, title=title)
        return textbook

    # ── 文档解析管线 ─────────────────────────────────

    async def trigger_parse(self, textbook_id: str) -> Textbook:
        """
        同步解析管线：
        1. 从 MinIO 下载文件
        2. 调用 parser 提取文本和章节
        3. 将章节写入数据库
        4. 更新 parse_status
        """
        import asyncio
        from functools import partial
        from shared.minio_client import download_file
        from content_engine.parser import parse_document

        tb = await self.get_textbook(textbook_id)

        if tb.parse_status not in ("pending", "failed"):
            logger.info(
                "parse_skipped",
                textbook_id=textbook_id,
                status=tb.parse_status,
            )
            return tb

        # 更新状态为 parsing
        tb.parse_status = "parsing"
        await self.db.flush()

        try:
            # 1. 下载文件
            file_data = await download_file(tb.source_file_url)
            filename = tb.source_file_url.rsplit("/", 1)[-1]

            # 2. 解析（同步 CPU 密集操作，放到线程池）
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, partial(parse_document, file_data, filename)
            )

            if result.error:
                logger.error(
                    "parse_failed",
                    textbook_id=textbook_id,
                    error=result.error,
                )
                tb.parse_status = "failed"
                await self.db.flush()
                return tb

            # 3. 章节入库（扁平写入，通过 depth 和 sort_order 保留结构）
            for ch in result.chapters:
                await self.create_chapter(
                    textbook_id=textbook_id,
                    title=ch.title,
                    depth=ch.depth,
                    sort_order=ch.sort_order,
                    content_text=ch.content,
                )

            # 4. 更新教材元数据
            tb.parse_status = "completed"
            if result.page_count:
                if tb.metadata is None:
                    tb.metadata = {}
                tb.metadata["page_count"] = result.page_count
                tb.metadata["chapter_count"] = len(result.chapters)

            await self.db.flush()
            logger.info(
                "parse_completed",
                textbook_id=textbook_id,
                chapters=len(result.chapters),
                pages=result.page_count,
                text_len=len(result.full_text),
            )
            return tb

        except Exception as e:
            logger.error(
                "parse_exception",
                textbook_id=textbook_id,
                error=str(e),
                exc_info=True,
            )
            tb.parse_status = "failed"
            await self.db.flush()
            return tb

    # ── 生成资源查询 ─────────────────────────────────

    async def get_generated_resource(self, resource_id: str) -> GeneratedResource:
        """获取单个生成资源详情。"""
        stmt = select(GeneratedResource).where(
            GeneratedResource.id == resource_id
        )
        result = await self.db.execute(stmt)
        gr = result.scalar_one_or_none()
        if not gr:
            raise NotFoundError("generated_resource", resource_id)
        return gr

    # ── LLM 知识点提取 ───────────────────────────────

    async def extract_knowledge_points(self, textbook_id: str) -> list[KnowledgePoint]:
        """
        基于章节内容，使用 LLM 提取知识点。
        流程：
        1. 获取教材下所有章节
        2. 对每个有内容的章节，调用 LLM 提取知识点
        3. 入库并返回
        """
        import json as json_mod
        from shared.llm_client import get_llm_client

        tb = await self.get_textbook(textbook_id)
        if tb.parse_status != "completed":
            raise ValidationError(f"教材尚未解析完成，当前状态: {tb.parse_status}")

        chapters = await self.get_chapter_tree(textbook_id)
        if not chapters:
            raise ValidationError("教材没有任何章节，请先解析")

        llm = get_llm_client()
        all_kps: list[KnowledgePoint] = []

        for chapter in chapters:
            content_text = chapter.content_text or ""
            if len(content_text.strip()) < 20:
                continue  # 内容太短，跳过

            # 截断过长内容，避免超 token 限制
            truncated = content_text[:6000]

            prompt = f"""你是一个教育领域的知识点提取专家。
请从以下教材章节内容中提取知识点，每个知识点包含：
- title: 知识点名称（简短）
- description: 知识点描述（1-2句话）
- difficulty: 难度（1-5，1最简单）
- bloom_level: 布鲁姆认知层次（remember/understand/apply/analyze/evaluate/create）
- tags: 标签数组

请以 JSON 数组格式返回，不要包含其他文本。

章节标题：{chapter.title}
章节内容：
{truncated}"""

            try:
                resp = await llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                content = resp.choices[0].message.content or ""
                # 尝试提取 JSON
                content = content.strip()
                if content.startswith("```"):
                    # 去掉 markdown code block
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1])
                kp_list = json_mod.loads(content)
            except Exception as e:
                logger.warning(
                    "kp_extract_llm_failed",
                    chapter_id=chapter.id,
                    error=str(e),
                )
                continue

            if not isinstance(kp_list, list):
                logger.warning("kp_extract_bad_format", chapter_id=chapter.id)
                continue

            for kp_data in kp_list:
                if not isinstance(kp_data, dict) or "title" not in kp_data:
                    continue
                kp = await self.create_knowledge_point(
                    chapter_id=str(chapter.id),
                    title=kp_data["title"],
                    description=kp_data.get("description", ""),
                    difficulty=kp_data.get("difficulty", 3),
                    bloom_level=kp_data.get("bloom_level", "understand"),
                    tags=kp_data.get("tags", []),
                )
                all_kps.append(kp)

            logger.info(
                "kp_extracted_for_chapter",
                chapter_id=str(chapter.id),
                count=len([k for k in kp_list if isinstance(k, dict)]),
            )

        logger.info(
            "kp_extraction_done",
            textbook_id=textbook_id,
            total_kps=len(all_kps),
        )
        return all_kps
