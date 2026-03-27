"""练习题生成 Service — 基于知识点 + Prompt 模板调用 LLM"""

import json
import logging
import uuid
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from content_engine.models import GeneratedResource, KnowledgePoint
from content_engine.prompt_service import get_active_template
from shared.exceptions import NotFoundError, BusinessError
from shared.llm_client import get_llm_client

logger = logging.getLogger(__name__)

# ── 题型常量 ──────────────────────────────────────────

EXERCISE_TYPES = ("choice", "fill_blank", "short_answer", "true_false")

RESOURCE_TYPE_MAP = {
    "choice": "exercise_choice",
    "fill_blank": "exercise_fill_blank",
    "short_answer": "exercise_short_answer",
    "true_false": "exercise_true_false",
}


# ── 核心生成 ──────────────────────────────────────────

async def generate_exercises(
    db: AsyncSession,
    *,
    kp_id: uuid.UUID,
    exercise_type: str = "choice",
    count: int = 5,
    difficulty: int = 3,
) -> GeneratedResource:
    """
    为指定知识点生成练习题。

    Returns: 保存后的 GeneratedResource 记录
    """
    if exercise_type not in EXERCISE_TYPES:
        raise BusinessError(f"不支持的题型: {exercise_type}，可选: {', '.join(EXERCISE_TYPES)}")
    if not 1 <= difficulty <= 5:
        raise BusinessError("difficulty 必须在 1-5 之间")
    if not 1 <= count <= 20:
        raise BusinessError("count 必须在 1-20 之间")

    # 1) 获取知识点
    kp = await db.get(KnowledgePoint, kp_id)
    if not kp:
        raise NotFoundError("knowledge_point", str(kp_id))

    # 2) 获取章节上下文
    chapter = await kp.awaitable_attrs.chapter if hasattr(kp, "awaitable_attrs") else kp.chapter
    chapter_title = chapter.title if chapter else "未知章节"

    # 3) 获取 prompt 模板
    resource_type = RESOURCE_TYPE_MAP[exercise_type]
    try:
        tpl = await get_active_template(db, resource_type)
        prompt_text = tpl.template_text
        tpl_id = tpl.id
    except NotFoundError:
        # 没有自定义模板时使用内置默认
        prompt_text = _default_prompt(exercise_type)
        tpl_id = None

    # 4) 构建 LLM prompt
    filled_prompt = prompt_text.format(
        kp_title=kp.title,
        kp_description=kp.description or "无详细描述",
        chapter_title=chapter_title,
        difficulty=difficulty,
        count=count,
        exercise_type=_type_cn(exercise_type),
    )

    # 5) 调用 LLM
    llm = get_llm_client()
    system_msg = (
        "你是一位专业的中小学教师，擅长根据知识点出题。"
        "你必须严格按照 JSON 格式输出，不要添加任何 markdown 代码块标记或额外文字。"
    )

    logger.info("Generating %d %s exercises for KP %s", count, exercise_type, kp_id)
    raw_response = await llm.chat(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": filled_prompt},
        ],
        temperature=0.7,
    )

    # 6) 解析 JSON
    content_json = _parse_llm_response(raw_response, exercise_type)

    # 7) 质量校验
    quality_score = _validate_exercises(content_json, exercise_type, count)

    # 8) 存入 DB
    resource = GeneratedResource(
        knowledge_point_id=kp_id,
        resource_type=resource_type,
        title=f"{kp.title} - {_type_cn(exercise_type)} ({count}题)",
        content_json=content_json,
        prompt_template_id=tpl_id,
        llm_model=llm.model_name,
        quality_score=quality_score,
    )
    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    logger.info("Saved exercise resource %s, quality=%s", resource.id, quality_score)
    return resource


# ── 查询 ──────────────────────────────────────────────

async def get_exercise(db: AsyncSession, resource_id: uuid.UUID) -> GeneratedResource:
    res = await db.get(GeneratedResource, resource_id)
    if not res or not res.resource_type.startswith("exercise_"):
        raise NotFoundError("exercise_resource", str(resource_id))
    return res


async def list_exercises_by_kp(
    db: AsyncSession,
    kp_id: uuid.UUID,
    exercise_type: Optional[str] = None,
) -> list[GeneratedResource]:
    stmt = select(GeneratedResource).where(
        and_(
            GeneratedResource.knowledge_point_id == kp_id,
            GeneratedResource.resource_type.like("exercise_%"),
        )
    )
    if exercise_type and exercise_type in RESOURCE_TYPE_MAP:
        stmt = stmt.where(
            GeneratedResource.resource_type == RESOURCE_TYPE_MAP[exercise_type]
        )
    stmt = stmt.order_by(GeneratedResource.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_exercises(
    db: AsyncSession,
    exercise_type: Optional[str] = None,
    min_difficulty: Optional[int] = None,
    max_difficulty: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[GeneratedResource]:
    stmt = select(GeneratedResource).where(
        GeneratedResource.resource_type.like("exercise_%")
    )
    if exercise_type and exercise_type in RESOURCE_TYPE_MAP:
        stmt = stmt.where(
            GeneratedResource.resource_type == RESOURCE_TYPE_MAP[exercise_type]
        )
    stmt = stmt.order_by(GeneratedResource.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── 内部工具函数 ──────────────────────────────────────

def _type_cn(exercise_type: str) -> str:
    return {
        "choice": "选择题",
        "fill_blank": "填空题",
        "short_answer": "简答题",
        "true_false": "判断题",
    }.get(exercise_type, exercise_type)


def _parse_llm_response(raw: str, exercise_type: str) -> dict:
    """从 LLM 原始输出提取 JSON"""
    text = raw.strip()
    # 去掉可能的 markdown code block
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 尝试找 { } 区间
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                raise BusinessError(f"LLM 返回的内容无法解析为 JSON:\n{text[:500]}")
        else:
            raise BusinessError(f"LLM 返回的内容无法解析为 JSON:\n{text[:500]}")

    # 规范化
    if "questions" not in data:
        if isinstance(data, list):
            data = {"exercise_type": exercise_type, "questions": data}
        else:
            raise BusinessError("LLM 返回的 JSON 缺少 questions 字段")

    data["exercise_type"] = exercise_type
    return data


def _validate_exercises(content_json: dict, exercise_type: str, expected_count: int) -> int:
    """
    校验练习题质量，返回 1-5 质量分。
    """
    questions = content_json.get("questions", [])
    if not questions:
        raise BusinessError("生成的练习题为空")

    score = 5
    issues = []

    # 数量检查
    if len(questions) < expected_count:
        score -= 1
        issues.append(f"期望 {expected_count} 题，实际 {len(questions)} 题")

    for i, q in enumerate(questions):
        # 题干检查
        if not q.get("stem"):
            score -= 1
            issues.append(f"第 {i+1} 题缺少题干")
            break  # 严重问题，不再逐题扣分

        # 答案检查
        if not q.get("answer") and q.get("answer") != False:
            score -= 1
            issues.append(f"第 {i+1} 题缺少答案")
            break

        # 选择题需要 options
        if exercise_type == "choice" and not q.get("options"):
            score -= 1
            issues.append(f"第 {i+1} 题(选择题)缺少选项")
            break

    if issues:
        logger.warning("Exercise quality issues: %s", "; ".join(issues))

    return max(1, score)


def _default_prompt(exercise_type: str) -> str:
    """内置默认 prompt 模板"""
    base = (
        "请根据以下知识点生成 {count} 道{exercise_type}，难度等级 {difficulty}（1-5，5最难）。\n\n"
        "【知识点】{kp_title}\n"
        "【描述】{kp_description}\n"
        "【所属章节】{chapter_title}\n\n"
    )

    if exercise_type == "choice":
        return base + (
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "题干", '
            '"options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}}, '
            '"answer": "B", "explanation": "解析", "difficulty": 3}}]}}\n'
            "注意：每题必须有4个选项，答案为正确选项字母，解析要清晰。"
        )
    elif exercise_type == "fill_blank":
        return base + (
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "题干（空白处用____表示）", '
            '"answer": "正确答案", "explanation": "解析", "difficulty": 3}}]}}\n'
            "注意：题干中用 ____ 标注填空位置。"
        )
    elif exercise_type == "short_answer":
        return base + (
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "题干", '
            '"answer": "参考答案", "key_points": ["要点1", "要点2"], '
            '"explanation": "解析", "difficulty": 3}}]}}\n'
            "注意：答案要完整，关键得分点要列出。"
        )
    elif exercise_type == "true_false":
        return base + (
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "判断题题干", '
            '"answer": true, "explanation": "解析", "difficulty": 3}}]}}\n'
            "注意：answer 为 true 或 false 布尔值。"
        )
    return base
