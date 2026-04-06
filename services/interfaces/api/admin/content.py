"""Admin 内容管理路由 — 教材 / 章节 / 知识点 / 资源生成 / Prompt 模板"""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File

from shared.response import ok, paged, paged
from interfaces.schemas.content import (
    TextbookCreate, TextbookUpdate, TextbookOut, TextbookDetail,
    ChapterTree,
    KnowledgePointCreate, KnowledgePointOut,
    GeneratedResourceOut, GenerateResourceRequest,
    ExerciseGenerateRequest, ExerciseCreate, ExerciseOut,
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateOut,
)
from interfaces.api.deps import AdminUser, ContentSvc, ExerciseSvc, PromptSvc

router = APIRouter(prefix="/api/v1/admin/content", tags=["admin-content"])


# ── 教材 CRUD ─────────────────────────────────────────

@router.post("/textbooks", summary="创建教材")
async def create_textbook(body: TextbookCreate, svc: ContentSvc, _admin: AdminUser):
    tb = await svc.create_textbook(body)
    return ok(TextbookOut.model_validate(tb).model_dump())


@router.get("/textbooks", summary="教材列表")
async def list_textbooks(
    svc: ContentSvc,
    _admin: AdminUser,
    subject: Optional[str] = Query(None),
    grade_range: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_textbooks(
        subject=subject, grade_range=grade_range,
        page=page, page_size=page_size,
    )
    data = [TextbookOut.model_validate(t).model_dump() for t in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.get("/textbooks/{textbook_id}", summary="教材详情（含章节树）")
async def get_textbook(textbook_id: UUID, svc: ContentSvc, _admin: AdminUser):
    detail = await svc.get_textbook_detail(textbook_id)
    return ok(TextbookDetail.model_validate(detail).model_dump())


@router.patch("/textbooks/{textbook_id}", summary="更新教材")
async def update_textbook(
    textbook_id: UUID, body: TextbookUpdate, svc: ContentSvc, _admin: AdminUser,
):
    tb = await svc.update_textbook(textbook_id, **body.model_dump(exclude_unset=True))
    return ok(TextbookOut.model_validate(tb).model_dump())


@router.delete("/textbooks/{textbook_id}", summary="删除教材（软删除）")
async def delete_textbook(textbook_id: UUID, svc: ContentSvc, _admin: AdminUser):
    await svc.delete_textbook(textbook_id)
    return ok()


@router.post("/textbooks/{textbook_id}/parse", summary="触发教材解析")
async def parse_textbook(textbook_id: UUID, svc: ContentSvc, _admin: AdminUser):
    result = await svc.parse_textbook(textbook_id)
    return ok(result)


# ── 章节 ──────────────────────────────────────────────

@router.get("/textbooks/{textbook_id}/chapters", summary="章节树")
async def get_chapter_tree(textbook_id: UUID, svc: ContentSvc, _admin: AdminUser):
    tree = await svc.get_chapter_tree(textbook_id)
    data = [ChapterTree.model_validate(c).model_dump() for c in tree]
    return ok(data)


# ── 知识点 ────────────────────────────────────────────

@router.post("/knowledge-points", summary="创建知识点")
async def create_knowledge_point(
    body: KnowledgePointCreate, svc: ContentSvc, _admin: AdminUser,
):
    kp = await svc.create_knowledge_point(body)
    return ok(KnowledgePointOut.model_validate(kp).model_dump())


@router.get("/chapters/{chapter_id}/knowledge-points", summary="章节下知识点列表")
async def list_knowledge_points(
    chapter_id: UUID, svc: ContentSvc, _admin: AdminUser,
):
    items = await svc.list_knowledge_points(chapter_id)
    data = [KnowledgePointOut.model_validate(kp).model_dump() for kp in items]
    return ok(data)


# ── 资源生成 ──────────────────────────────────────────

@router.post("/resources/generate", summary="生成教学资源")
async def generate_resource(
    body: GenerateResourceRequest, svc: ContentSvc, _admin: AdminUser,
):
    resource = await svc.generate_resource(body)
    return ok(GeneratedResourceOut.model_validate(resource).model_dump())


# ── 习题 ──────────────────────────────────────────────

@router.post("/exercises/generate", summary="AI 生成习题")
async def generate_exercises(
    body: ExerciseGenerateRequest, svc: ExerciseSvc, _admin: AdminUser,
):
    exercises = await svc.generate_exercises(body)
    data = [ExerciseOut.model_validate(e).model_dump() for e in exercises]
    return ok(data)


@router.post("/exercises", summary="手动创建习题")
async def create_exercise(body: ExerciseCreate, svc: ExerciseSvc, _admin: AdminUser):
    ex = await svc.create_exercise(body)
    return ok(ExerciseOut.model_validate(ex).model_dump())


# ── Prompt 模板 ──────────────────────────────────────

@router.post("/prompt-templates", summary="创建 Prompt 模板")
async def create_prompt_template(
    body: PromptTemplateCreate, svc: PromptSvc, _admin: AdminUser,
):
    tpl = await svc.create_template(body)
    return ok(PromptTemplateOut.model_validate(tpl).model_dump())


@router.get("/prompt-templates", summary="Prompt 模板列表")
async def list_prompt_templates(
    svc: PromptSvc,
    _admin: AdminUser,
    scene: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_templates(
        scene=scene, page=page, page_size=page_size,
    )
    data = [PromptTemplateOut.model_validate(t).model_dump() for t in items]
    return paged(data, total=total, page=page, page_size=page_size)


@router.patch("/prompt-templates/{template_id}", summary="更新 Prompt 模板")
async def update_prompt_template(
    template_id: UUID,
    body: PromptTemplateUpdate,
    svc: PromptSvc,
    _admin: AdminUser,
):
    tpl = await svc.update_template(template_id, body)
    return ok(PromptTemplateOut.model_validate(tpl).model_dump())


@router.delete("/prompt-templates/{template_id}", summary="删除 Prompt 模板（软删除）")
async def delete_prompt_template(
    template_id: UUID, svc: PromptSvc, _admin: AdminUser,
):
    await svc.delete_template(template_id)
    return ok()
