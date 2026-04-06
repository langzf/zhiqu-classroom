"""content_engine 数据模型 — content schema, 6 张表"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from shared.base_model import Base, TimestampMixin, SoftDeleteMixin, generate_uuid7


# ── textbooks ─────────────────────────────────────────

class Textbook(Base, TimestampMixin, SoftDeleteMixin):
    """教材"""
    __tablename__ = "textbooks"
    __table_args__ = (
        Index("idx_textbooks_subject", "subject"),
        Index("idx_textbooks_grade", "grade_range"),
        Index("idx_textbooks_status", "parse_status"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="math/chinese/english/physics/chemistry/biology/history/geography/politics",
    )
    grade_range: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="grade_7-grade_9"
    )
    source_file_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="MinIO 原始文件地址"
    )
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending/parsing/completed/failed",
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, comment="额外元信息"
    )

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="textbook", lazy="selectin",
        order_by="Chapter.sort_order",
    )


# ── chapters ──────────────────────────────────────────

class Chapter(Base, TimestampMixin):
    """章节 — 自引用树结构，深度 ≤ 4"""
    __tablename__ = "chapters"
    __table_args__ = (
        Index("idx_chapters_textbook", "textbook_id"),
        Index("idx_chapters_parent", "parent_id"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    textbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content.textbooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content.chapters.id", ondelete="CASCADE"),
        nullable=True,
        comment="父章节，NULL 表示顶层",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="该章节提取的文本内容"
    )

    textbook: Mapped["Textbook"] = relationship(back_populates="chapters")
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        back_populates="chapter", lazy="selectin",
    )


# ── knowledge_points ──────────────────────────────────

class KnowledgePoint(Base, TimestampMixin):
    """知识点"""
    __tablename__ = "knowledge_points"
    __table_args__ = (
        Index("idx_kp_chapter", "chapter_id"),
        Index("idx_kp_difficulty", "difficulty"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content.chapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="1-5"
    )
    bloom_level: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        comment="remember/understand/apply/analyze/evaluate/create",
    )
    tags: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=None,
    )

    chapter: Mapped["Chapter"] = relationship(back_populates="knowledge_points")
    embeddings: Mapped[list["KpEmbedding"]] = relationship(
        back_populates="knowledge_point", lazy="noload",
    )


# ── kp_embeddings ─────────────────────────────────────

class KpEmbedding(Base, TimestampMixin):
    """知识点向量 — 支持多模型"""
    __tablename__ = "kp_embeddings"
    __table_args__ = (
        Index("idx_kpe_kp", "knowledge_point_id"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content.knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="embedding 模型名"
    )
    embedding = mapped_column(
        Vector(1024), nullable=False, comment="向量"
    )
    source_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="用于生成向量的原文"
    )

    knowledge_point: Mapped["KnowledgePoint"] = relationship(
        back_populates="embeddings"
    )


# ── generated_resources ───────────────────────────────

class GeneratedResource(Base, TimestampMixin):
    """AI 生成的教学资源"""
    __tablename__ = "generated_resources"
    __table_args__ = (
        Index("idx_gr_kp", "knowledge_point_id"),
        Index("idx_gr_type", "resource_type"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content.knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="quiz/game/video_script/summary/exercise",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="资源内容 JSON"
    )
    prompt_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="生成时使用的 prompt 模板",
    )
    llm_model: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="生成使用的 LLM 模型"
    )
    quality_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="质量评分 1-5"
    )


# ── prompt_templates ──────────────────────────────────

class PromptTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Prompt 模板 — 版本管理"""
    __tablename__ = "prompt_templates"
    __table_args__ = (
        Index("idx_pt_type_active", "resource_type", "is_active"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    resource_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="对应 resource_type"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
