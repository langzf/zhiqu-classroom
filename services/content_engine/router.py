"""
content_engine 路由
───────────────────
路径前缀：/api/v1/content
MVP 端点：教材 CRUD + 解析触发、章节树、知识点列表、
         向量搜索、生成资源列表
"""

from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form

from database import get_db
from deps import get_current_user, require_role
from shared.exceptions import NotFoundError, ValidationError
from shared.schemas import ok, paged
from shared.security import TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from content_engine.schemas import (
    ChapterOut,
    ExerciseGenerateRequest,
    ExerciseOut,
    GeneratedResourceOut,
    KnowledgePointOut,
    KpSearchRequest,
    PromptTemplateCreate,
    PromptTemplateOut,
    PromptTemplateUpdate,
    TextbookCreate,
    TextbookOut,
    TextbookUpdate,
)
from content_engine.service import ContentService
from content_engine import exercise_service, prompt_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/content", tags=["content-engine"])


# ── 内部依赖 ──────────────────────────────────────────

def _build_service(db: AsyncSession = Depends(get_db)) -> ContentService:
    return ContentService(db=db)


Svc = Annotated[ContentService, Depends(_build_service)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 教材
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/textbooks")
async def create_textbook(body: TextbookCreate, user: AdminUser, svc: Svc):
    """
    创建教材记录（管理员）
    - 记录教材元信息 + 源文件 URL
    - parse_status 初始为 pending
    """
    tb = await svc.create_textbook(
        title=body.title,
        subject=body.subject,
        grade_range=body.grade_range,
        source_file_url=body.source_file_url,
    )
    return ok(TextbookOut.model_validate(tb).model_dump())


@router.post("/textbooks/upload")
async def upload_textbook(
    user: AdminUser,
    svc: Svc,
    file: UploadFile = File(..., description="PDF 或 DOCX 文件，最大 50MB"),
    title: str = Form(..., description="教材标题"),
    subject: str = Form(..., description="学科"),
    grade_range: str = Form(..., description="年级范围"),
):
    """
    上传教材文件（管理员）
    - 上传文件到 MinIO
    - 创建教材记录（parse_status = pending）
    - 自动触发解析
    """
    # 校验文件类型
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx"):
        raise ValidationError(f"不支持的文件类型: .{ext}（仅支持 PDF/DOCX）")

    # 读取文件数据
    file_data = await file.read()
    if len(file_data) > 50 * 1024 * 1024:  # 50MB
        raise ValidationError("文件大小超过 50MB 限制")

    # 上传 + 创建记录
    tb = await svc.upload_and_create_textbook(
        title=title,
        subject=subject,
        grade_range=grade_range,
        filename=filename,
        file_data=file_data,
        content_type=file.content_type or "application/octet-stream",
    )

    # MVP: 同步触发解析
    tb = await svc.trigger_parse(tb.id)
    await svc.db.commit()

    logger.info("textbook_uploaded_and_parsed", textbook_id=tb.id, status=tb.parse_status)
    return ok(TextbookOut.model_validate(tb).model_dump())


@router.get("/textbooks")
async def list_textbooks(
    user: CurrentUser,
    svc: Svc,
    subject: Optional[str] = Query(None, description="学科过滤"),
    grade_range: Optional[str] = Query(None, description="年级范围过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """教材列表（分页 + 筛选）"""
    items, total = await svc.list_textbooks(
        subject=subject,
        grade_range=grade_range,
        page=page,
        page_size=page_size,
    )
    return paged(
        items=[TextbookOut.model_validate(i).model_dump() for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/textbooks/{textbook_id}")
async def get_textbook(textbook_id: str, user: CurrentUser, svc: Svc):
    """获取教材详情"""
    tb = await svc.get_textbook(textbook_id)
    return ok(TextbookOut.model_validate(tb).model_dump())


@router.patch("/textbooks/{textbook_id}")
async def update_textbook(
    textbook_id: str, body: TextbookUpdate, user: AdminUser, svc: Svc
):
    """更新教材信息（管理员）"""
    tb = await svc.get_textbook(textbook_id)
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(tb, k, v)
    await svc.db.flush()
    logger.info("textbook_updated", textbook_id=textbook_id, fields=list(update_data.keys()))
    return ok(TextbookOut.model_validate(tb).model_dump())


@router.post("/textbooks/{textbook_id}/parse")
async def trigger_parse(textbook_id: str, user: AdminUser, svc: Svc):
    """
    触发教材解析（管理员）
    - 下载文件 → 解析 → 创建章节
    - 支持重新解析（pending/failed 状态）
    """
    tb = await svc.trigger_parse(textbook_id)
    await svc.db.commit()
    logger.info("textbook_parse_triggered", textbook_id=textbook_id, status=tb.parse_status)
    return ok({"textbook_id": textbook_id, "parse_status": tb.parse_status})


@router.delete("/textbooks/{textbook_id}")
async def delete_textbook(textbook_id: str, user: AdminUser, svc: Svc):
    """软删除教材（管理员）"""
    tb = await svc.soft_delete_textbook(textbook_id)
    return ok({"textbook_id": textbook_id, "deleted": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 章节
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/textbooks/{textbook_id}/chapters")
async def get_chapter_tree(textbook_id: str, user: CurrentUser, svc: Svc):
    """
    获取教材的章节树
    - 平铺返回所有章节，客户端按 parent_id + depth 组装树
    """
    # 先确认教材存在
    await svc.get_textbook(textbook_id)
    chapters = await svc.get_chapter_tree(textbook_id)
    tree = _build_tree([ChapterOut.model_validate(c).model_dump() for c in chapters])
    return ok(tree)


def _build_tree(flat: list[dict]) -> list[dict]:
    """将平铺章节列表组装为嵌套树"""
    by_id = {c["id"]: {**c, "children": []} for c in flat}
    roots: list[dict] = []
    for c in by_id.values():
        pid = c.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(c)
        else:
            roots.append(c)
    return roots


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 知识点
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/chapters/{chapter_id}/knowledge-points")
async def list_knowledge_points(chapter_id: str, user: CurrentUser, svc: Svc):
    """获取某章节下的知识点列表"""
    kps = await svc.list_knowledge_points(chapter_id)
    return ok([KnowledgePointOut.model_validate(kp).model_dump() for kp in kps])


@router.get("/knowledge-points/{kp_id}")
async def get_knowledge_point(kp_id: str, user: CurrentUser, svc: Svc):
    """获取知识点详情"""
    kp = await svc.get_knowledge_point(kp_id)
    return ok(KnowledgePointOut.model_validate(kp).model_dump())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 向量搜索
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/knowledge-points/search")
async def search_knowledge_points(body: KpSearchRequest, user: CurrentUser, svc: Svc):
    """
    向量相似度搜索知识点（RAG 检索）
    - 传入 query_embedding（已编码的向量）
    - 返回 top-K 相似知识点
    """
    results = await svc.search_similar_kp(
        query_embedding=body.query_embedding,
        limit=body.limit,
        model_name=body.model_name,
    )
    return ok(results)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 生成资源
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/knowledge-points/{kp_id}/resources")
async def list_generated_resources(
    kp_id: str,
    user: CurrentUser,
    svc: Svc,
    resource_type: Optional[str] = Query(
        None, description="资源类型: quiz|game|video_script|summary|exercise"
    ),
):
    """获取某知识点下的生成资源列表"""
    resources = await svc.list_generated_resources(kp_id, resource_type)
    return ok(
        [GeneratedResourceOut.model_validate(r).model_dump() for r in resources]
    )


@router.get("/resources/{resource_id}")
async def get_generated_resource(resource_id: str, user: CurrentUser, svc: Svc):
    """获取生成资源详情"""
    resource = await svc.get_generated_resource(resource_id)
    return ok(GeneratedResourceOut.model_validate(resource).model_dump())


# ── 知识点提取 ────────────────────────────────────────


@router.post("/textbooks/{textbook_id}/extract-kp")
async def extract_knowledge_points(textbook_id: str, user: AdminUser, svc: Svc):
    """
    LLM 提取知识点（管理员）
    - 需要教材已解析完成（parse_status = completed）
    - 遍历章节内容，调用 LLM 提取知识点
    """
    kps = await svc.extract_knowledge_points(textbook_id)
    await svc.db.commit()
    return ok({
        "textbook_id": textbook_id,
        "knowledge_points_count": len(kps),
        "knowledge_points": [
            KnowledgePointOut.model_validate(kp).model_dump() for kp in kps
        ],
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 练习题生成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/exercises/generate")
async def generate_exercises_endpoint(
    body: ExerciseGenerateRequest, user: AdminUser, svc: Svc
):
    """
    AI 生成练习题（管理员）
    - 基于知识点 + prompt 模板调用 LLM 生成题目
    - 支持选择题/填空题/简答题/判断题
    """
    resource = await exercise_service.generate_exercises(
        svc.db,
        kp_id=body.knowledge_point_id,
        exercise_type=body.exercise_type,
        count=body.count,
        difficulty=body.difficulty,
    )
    await svc.db.commit()
    return ok(ExerciseOut.model_validate(resource).model_dump())


@router.get("/exercises/{resource_id}")
async def get_exercise(resource_id: str, user: CurrentUser, svc: Svc):
    """获取单套练习题"""
    import uuid as _uuid
    resource = await exercise_service.get_exercise(svc.db, _uuid.UUID(resource_id))
    return ok(ExerciseOut.model_validate(resource).model_dump())


@router.get("/knowledge-points/{kp_id}/exercises")
async def list_exercises_by_kp(
    kp_id: str,
    user: CurrentUser,
    svc: Svc,
    exercise_type: Optional[str] = Query(None, description="题型: choice/fill_blank/short_answer/true_false"),
):
    """获取某知识点下的练习题列表"""
    import uuid as _uuid
    resources = await exercise_service.list_exercises_by_kp(
        svc.db, _uuid.UUID(kp_id), exercise_type
    )
    return ok([ExerciseOut.model_validate(r).model_dump() for r in resources])


@router.get("/exercises")
async def list_exercises(
    user: CurrentUser,
    svc: Svc,
    exercise_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """练习题列表查询"""
    resources = await exercise_service.list_exercises(
        svc.db, exercise_type=exercise_type, limit=limit, offset=offset
    )
    return ok([ExerciseOut.model_validate(r).model_dump() for r in resources])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt 模板管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/prompts")
async def create_prompt(body: PromptTemplateCreate, user: AdminUser, svc: Svc):
    """创建 Prompt 模板（管理员）"""
    tpl = await prompt_service.create_prompt_template(
        svc.db,
        resource_type=body.resource_type,
        name=body.name,
        template_text=body.template_text,
        description=body.description,
        is_active=body.is_active,
    )
    await svc.db.commit()
    return ok(PromptTemplateOut.model_validate(tpl).model_dump())


@router.get("/prompts")
async def list_prompts(
    user: CurrentUser,
    svc: Svc,
    resource_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
):
    """查询 Prompt 模板列表"""
    tpls = await prompt_service.list_prompt_templates(
        svc.db, resource_type=resource_type, active_only=active_only
    )
    return ok([PromptTemplateOut.model_validate(t).model_dump() for t in tpls])


@router.get("/prompts/{tpl_id}")
async def get_prompt(tpl_id: str, user: CurrentUser, svc: Svc):
    """获取 Prompt 模板详情"""
    import uuid as _uuid
    tpl = await prompt_service.get_prompt_template(svc.db, _uuid.UUID(tpl_id))
    return ok(PromptTemplateOut.model_validate(tpl).model_dump())


@router.patch("/prompts/{tpl_id}")
async def update_prompt(tpl_id: str, body: PromptTemplateUpdate, user: AdminUser, svc: Svc):
    """更新 Prompt 模板（管理员）"""
    import uuid as _uuid
    tpl = await prompt_service.update_prompt_template(
        svc.db, _uuid.UUID(tpl_id), **body.model_dump(exclude_unset=True)
    )
    await svc.db.commit()
    return ok(PromptTemplateOut.model_validate(tpl).model_dump())


@router.post("/prompts/{tpl_id}/activate")
async def activate_prompt(tpl_id: str, user: AdminUser, svc: Svc):
    """激活指定模板，停用同类型其他模板（管理员）"""
    import uuid as _uuid
    tpl = await prompt_service.activate_template(svc.db, _uuid.UUID(tpl_id))
    await svc.db.commit()
    return ok(PromptTemplateOut.model_validate(tpl).model_dump())
