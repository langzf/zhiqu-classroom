"""content_engine Pydantic schemas"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field

from shared.schemas import OrmBase


# ── Textbook ──────────────────────────────────────────

class TextbookCreate(BaseModel):
    title: str = Field(..., max_length=200)
    subject: str = Field(...)
    grade_range: str = Field(..., description="grade_7-grade_9")
    source_file_url: str = Field(..., description="MinIO 文件 URL")


class TextbookUpdate(BaseModel):
    """教材更新 — 所有字段可选"""
    title: Optional[str] = Field(None, max_length=200)
    subject: Optional[str] = None
    grade_range: Optional[str] = None
    cover_url: Optional[str] = None


class TextbookOut(OrmBase):
    id: UUID
    title: str
    subject: str
    grade_range: str
    source_file_url: str
    cover_url: Optional[str] = None
    parse_status: str
    created_at: datetime


class TextbookDetail(TextbookOut):
    chapters: list["ChapterOut"] = []


# ── Chapter ───────────────────────────────────────────

class ChapterOut(OrmBase):
    id: UUID
    textbook_id: UUID
    parent_id: Optional[UUID] = None
    title: str
    depth: int
    sort_order: int


class ChapterTree(ChapterOut):
    children: list["ChapterTree"] = []
    knowledge_points: list["KnowledgePointOut"] = []


# ── Knowledge Point ───────────────────────────────────

class KnowledgePointOut(OrmBase):
    id: UUID
    chapter_id: UUID
    title: str
    description: Optional[str] = None
    difficulty: int
    bloom_level: Optional[str] = None
    tags: Optional[dict] = None


class KnowledgePointCreate(BaseModel):
    chapter_id: UUID
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)
    bloom_level: Optional[str] = None
    tags: Optional[dict] = None


# ── Vector Search ─────────────────────────────────────

class KpSearchRequest(BaseModel):
    """向量相似度搜索请求"""
    query_embedding: list[float] = Field(..., description="1024 维向量")
    limit: int = Field(default=10, ge=1, le=50)
    model_name: str = Field(default="default", description="Embedding 模型名")


# ── Generated Resource ────────────────────────────────

class GeneratedResourceOut(OrmBase):
    id: UUID
    knowledge_point_id: UUID
    resource_type: str
    title: str
    content_json: dict
    llm_model: Optional[str] = None
    quality_score: Optional[int] = None
    created_at: datetime


class GenerateResourceRequest(BaseModel):
    knowledge_point_id: UUID
    resource_type: str = Field(..., description="quiz/game/video_script/summary/exercise")
    extra_instructions: Optional[str] = None


# ── Exercise Generation ───────────────────────────────

class ExerciseGenerateRequest(BaseModel):
    """练习题生成请求"""
    knowledge_point_id: UUID
    exercise_type: str = Field(
        default="choice",
        description="题型: choice, fill_blank, short_answer, true_false",
    )
    count: int = Field(default=5, ge=1, le=20, description="生成题目数量")
    difficulty: int = Field(default=3, ge=1, le=5, description="难度 1-5")


class ExerciseCreate(BaseModel):
    """手动创建练习题"""
    knowledge_point_id: UUID
    exercise_type: str = Field(default="choice", description="choice/fill_blank/short_answer/true_false")
    title: str = Field(default="手动创建的练习", max_length=200)
    content: dict = Field(default_factory=dict)
    answer: Optional[dict] = None
    difficulty: int = Field(default=3, ge=1, le=5)


class ExerciseOut(OrmBase):
    """练习题资源输出"""
    id: UUID
    knowledge_point_id: Optional[UUID] = None
    resource_type: str
    title: str
    content_json: dict
    llm_model: Optional[str] = None
    quality_score: Optional[int] = None
    prompt_template_id: Optional[UUID] = None
    created_at: datetime


# ── Prompt Template ───────────────────────────────────

class PromptTemplateCreate(BaseModel):
    resource_type: str
    name: str = Field(..., max_length=100)
    template_text: str
    description: Optional[str] = None
    is_active: bool = True


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    template_text: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PromptTemplateOut(OrmBase):
    id: UUID
    resource_type: str
    name: str
    template_text: str
    description: Optional[str] = None
    is_active: bool
    version: int


# forward refs
ChapterTree.model_rebuild()
TextbookDetail.model_rebuild()
