"""内容引擎 — Admin 路由

前缀: /api/v1/admin/content
所有端点要求 admin 角色。
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File, Form, BackgroundTasks

from deps import DbSession, AdminUser, AppSettings
from shared.schemas import ok, paged
from content_engine import service, schemas

router = APIRouter(prefix="/content", tags=["admin-content"])


# ── 教材 CRUD ─────────────────────────────────────────

@router.post("/textbooks")
async def create_textbook(body: schemas.TextbookCreate, db: DbSession, user: AdminUser):
    tb = await service.create_textbook(db, body, created_by=user.sub)
    return ok(tb)


@router.get("/textbooks")
async def list_textbooks(
    db: DbSession,
    user: AdminUser,
    subject: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.list_textbooks(
        db, subject=subject, grade=grade, status=status,
        page=page, page_size=page_size,
    )
    return paged(items, total, page, page_size)


@router.get("/textbooks/{textbook_id}")
async def get_textbook(textbook_id: UUID, db: DbSession, user: AdminUser):
    tb = await service.get_textbook(db, textbook_id)
    return ok(tb)


@router.patch("/textbooks/{textbook_id}")
async def update_textbook(
    textbook_id: UUID, body: schemas.TextbookUpdate,
    db: DbSession, user: AdminUser,
):
    tb = await service.update_textbook(db, textbook_id, body)
    return ok(tb)


@router.delete("/textbooks/{textbook_id}")
async def delete_textbook(textbook_id: UUID, db: DbSession, user: AdminUser):
    await service.delete_textbook(db, textbook_id)
    return ok({"textbook_id": str(textbook_id), "deleted": True})


# ── 教材上传 & 解析 ───────────────────────────────────

@router.post("/textbooks/upload")
async def upload_textbook(
    db: DbSession,
    user: AdminUser,
    settings: AppSettings,
    file: UploadFile = File(...),
    title: str = Form(...),
    subject: str = Form(...),
    grade: str = Form(...),
    publisher: Optional[str] = Form(None),
):
    tb = await service.upload_and_create_textbook(
        db, settings=settings, file=file,
        title=title, subject=subject, grade=grade,
        publisher=publisher, created_by=user.sub,
    )
    return ok(tb)


@router.post("/textbooks/{textbook_id}/parse")
async def trigger_parse(
    textbook_id: UUID,
    db: DbSession,
    user: AdminUser,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
):
    tb = await service.trigger_parse(db, textbook_id, settings, background_tasks)
    return ok(tb)


# ── 章节 ──────────────────────────────────────────────

@router.get("/textbooks/{textbook_id}/chapters")
async def get_chapters(textbook_id: UUID, db: DbSession, user: AdminUser):
    chapters = await service.get_chapters(db, textbook_id)
    return ok(chapters)


# ── 知识点 ────────────────────────────────────────────

@router.get("/knowledge-points")
async def list_knowledge_points(
    db: DbSession,
    user: AdminUser,
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
    user: AdminUser,
    settings: AppSettings,
):
    results = await service.search_knowledge_points(db, settings, body)
    return ok(results)


@router.get("/knowledge-points/{kp_id}/resources")
async def get_kp_resources(kp_id: UUID, db: DbSession, user: AdminUser):
    resources = await service.get_generated_resources(db, kp_id)
    return ok(resources)


# ── 练习题 ────────────────────────────────────────────

@router.post("/exercises/generate")
async def generate_exercises(
    body: schemas.ExerciseGenerateRequest,
    db: DbSession,
    user: AdminUser,
    settings: AppSettings,
):
    from content_engine.exercise_service import generate_exercises as gen
    resource = await gen(db, settings, body)
    return ok(resource)


@router.get("/exercises")
async def list_exercises(
    db: DbSession,
    user: AdminUser,
    exercise_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    exercises = await service.list_exercises(
        db, exercise_type=exercise_type, limit=limit, offset=offset,
    )
    return ok(exercises)


@router.get("/exercises/{resource_id}")
async def get_exercise(resource_id: UUID, db: DbSession, user: AdminUser):
    resource = await service.get_generated_resource(db, resource_id)
    return ok(resource)
