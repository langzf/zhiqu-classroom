"""App 内容浏览路由 — 学生端教材 / 章节 / 知识点 / 搜索"""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Query

from shared.response import ok, paged
from interfaces.schemas.content import (
    TextbookOut, TextbookDetail, ChapterTree,
    KnowledgePointOut, KpSearchRequest,
)
from interfaces.api.deps import CurrentUser, ContentSvc

router = APIRouter(prefix="/api/v1/app/content", tags=["app-content"])


@router.get("/textbooks", summary="教材列表（学生浏览）")
async def list_textbooks(
    _user: CurrentUser,
    svc: ContentSvc,
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


@router.get("/textbooks/{textbook_id}", summary="教材详情")
async def get_textbook(textbook_id: UUID, _user: CurrentUser, svc: ContentSvc):
    detail = await svc.get_textbook_detail(textbook_id)
    return ok(TextbookDetail.model_validate(detail).model_dump())


@router.get("/textbooks/{textbook_id}/chapters", summary="章节树")
async def get_chapter_tree(textbook_id: UUID, _user: CurrentUser, svc: ContentSvc):
    tree = await svc.get_chapter_tree(textbook_id)
    data = [ChapterTree.model_validate(c).model_dump() for c in tree]
    return ok(data)


@router.get("/chapters/{chapter_id}/knowledge-points", summary="知识点列表")
async def list_knowledge_points(
    chapter_id: UUID, _user: CurrentUser, svc: ContentSvc,
):
    items, _total = await svc.list_knowledge_points(str(chapter_id))
    data = [KnowledgePointOut.model_validate(kp).model_dump() for kp in items]
    return ok(data)


@router.post("/knowledge-points/search", summary="知识点语义搜索")
async def search_knowledge_points(
    body: KpSearchRequest, _user: CurrentUser, svc: ContentSvc,
):
    results = await svc.search_knowledge_points_by_query(body)
    return ok(results)
