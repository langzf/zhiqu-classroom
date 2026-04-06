"""管理后台 – 内容引擎路由"""
from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from content_engine.schemas import (
    ChapterTree,
    ExerciseCreate,
    ExerciseOut,
    KnowledgePointCreate,
    KnowledgePointOut,
    TextbookCreate,
    TextbookOut,
    TextbookUpdate,
)
from content_engine.service import ContentService
from database import get_db
from deps import AdminUser, DbSession
from shared.schemas import ok, paged

router = APIRouter(prefix="/content", tags=["admin-content"])


# ── DI ────────────────────────────────────────────────
def _build_service(db: DbSession) -> ContentService:
    return ContentService(db)


Svc = Annotated[ContentService, Depends(_build_service)]


# ══════════════════  教材  ══════════════════
@router.get("/textbooks")
async def list_textbooks(
    svc: Svc,
    _user: AdminUser,
    subject: Optional[str] = Query(None),
    grade_range: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_textbooks(
        subject=subject,
        grade_range=grade_range,
        page=page,
        page_size=page_size,
    )
    return paged(items, total, page, page_size)


@router.post("/textbooks", status_code=201)
async def create_textbook(svc: Svc, _user: AdminUser, body: TextbookCreate):
    tb = await svc.create_textbook(
        title=body.title,
        subject=body.subject,
        grade_range=body.grade_range,
        source_file_url=body.source_file_url,
    )
    return ok(tb)


@router.get("/textbooks/{textbook_id}")
async def get_textbook(svc: Svc, _user: AdminUser, textbook_id: str):
    tb = await svc.get_textbook(textbook_id)
    return ok(tb)


@router.put("/textbooks/{textbook_id}")
async def update_textbook(
    svc: Svc, _user: AdminUser, textbook_id: str, body: TextbookUpdate
):
    data = body.model_dump(exclude_unset=True)
    tb = await svc.update_textbook(textbook_id, **data)
    return ok(tb)


@router.delete("/textbooks/{textbook_id}")
async def delete_textbook(svc: Svc, _user: AdminUser, textbook_id: str):
    await svc.delete_textbook(textbook_id)
    return ok(msg="deleted")


# ══════════════════  章节  ══════════════════
@router.get("/textbooks/{textbook_id}/chapters")
async def get_chapters(svc: Svc, _user: AdminUser, textbook_id: str):
    chapters = await svc.get_chapters(textbook_id)
    return ok(chapters)


@router.post("/textbooks/{textbook_id}/chapters", status_code=201)
async def create_chapter(svc: Svc, _user: AdminUser, textbook_id: str, body: dict):
    ch = await svc.create_chapter(
        textbook_id=textbook_id,
        title=body.get("title", ""),
        parent_id=body.get("parent_id"),
        sort_order=body.get("sort_order", 0),
    )
    return ok(ch)


# ══════════════════  知识点  ══════════════════
@router.get("/knowledge-points")
async def list_knowledge_points(
    svc: Svc,
    _user: AdminUser,
    chapter_id: Optional[str] = Query(None),
):
    items = await svc.list_knowledge_points(chapter_id=chapter_id)
    return ok(items)


@router.post("/knowledge-points", status_code=201)
async def create_knowledge_point(
    svc: Svc, _user: AdminUser, body: KnowledgePointCreate
):
    kp = await svc.create_knowledge_point(
        chapter_id=str(body.chapter_id),
        title=body.title,
        description=body.description,
        difficulty=body.difficulty,
        bloom_level=body.bloom_level,
        tags=body.tags,
    )
    return ok(kp)


# ══════════════════  练习题  ══════════════════
@router.get("/exercises")
async def list_exercises(
    svc: Svc,
    _user: AdminUser,
    knowledge_point_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await svc.get_exercises(
        knowledge_point_id=knowledge_point_id,
        page=page,
        page_size=page_size,
    )
    return paged(items, total, page, page_size)


@router.post("/exercises", status_code=201)
async def create_exercise(svc: Svc, _user: AdminUser, body: ExerciseCreate):
    ex = await svc.create_exercise(
        knowledge_point_id=str(body.knowledge_point_id),
        exercise_type=body.exercise_type,
        title=body.title,
        content=body.content,
        answer=body.answer,
        difficulty=body.difficulty,
    )
    return ok(ex)
