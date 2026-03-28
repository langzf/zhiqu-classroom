"""内容引擎 — 学生端路由

前缀: /api/v1/content
面向学生/家长，只读查询为主。
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query

from deps import DbSession, CurrentUser, AppSettings
from shared.schemas import ok, paged
from content_engine import service, schemas

router = APIRouter(prefix="/content", tags=["student-content"])


# ── 教材（只读）───────────────────────────────────────

@router.get("/textbooks")
async def list_textbooks(
    db: DbSession,
    user: CurrentUser,
    subject: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_textbooks(
        db, subject=subject, grade=grade, status="active",
        page=page, page_size=page_size,
    )
    return paged(items, total, page, page_size)


@router.get("/textbooks/{textbook_id}")
async def get_textbook(textbook_id: UUID, db: DbSession, user: CurrentUser):
    tb = await service.get_textbook(db, textbook_id)
    return ok(tb)


@router.get("/textbooks/{textbook_id}/chapters")
async def get_chapters(textbook_id: UUID, db: DbSession, user: CurrentUser):
    chapters = await service.get_chapters(db, textbook_id)
    return ok(chapters)


# ── 知识点（只读）─────────────────────────────────────

@router.get("/knowledge-points")
async def list_knowledge_points(
    db: DbSession,
    user: CurrentUser,
    subject: Optional[str] = Query(None),
    chapter_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_knowledge_points(
        db, subject=subject, chapter_id=chapter_id,
        page=page, page_size=page_size,
    )
    return paged(items, total, page, page_size)


@router.post("/knowledge-points/search")
async def search_knowledge_points(
    body: schemas.KpSearchRequest,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
):
    results = await service.search_knowledge_points(db, settings, body)
    return ok(results)


# ── 练习题 / 资源（只读）──────────────────────────────

@router.get("/exercises")
async def list_exercises(
    db: DbSession,
    user: CurrentUser,
    exercise_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    exercises = await service.list_exercises(
        db, exercise_type=exercise_type, limit=limit, offset=offset,
    )
    return ok(exercises)


@router.get("/exercises/{resource_id}")
async def get_exercise(resource_id: UUID, db: DbSession, user: CurrentUser):
    resource = await service.get_generated_resource(db, resource_id)
    return ok(resource)


@router.get("/knowledge-points/{kp_id}/resources")
async def get_kp_resources(kp_id: UUID, db: DbSession, user: CurrentUser):
    resources = await service.get_generated_resources(db, kp_id)
    return ok(resources)
