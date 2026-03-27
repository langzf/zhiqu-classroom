"""
初始化数据库 — 创建 schema、启用扩展、建表、种子数据
用法: python init_db.py
"""

import asyncio
import sys

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import get_settings

# ── 导入所有 models 使其注册到 Base.metadata ──
from shared.base_model import Base
import user_profile.models  # noqa: F401
import content_engine.models  # noqa: F401
import ai_tutor.models  # noqa: F401
import learning_orchestrator.models  # noqa: F401

from content_engine.models import PromptTemplate


# ── 默认 Prompt 模板 ──────────────────────────────────

DEFAULT_PROMPTS = [
    {
        "resource_type": "exercise_choice",
        "name": "默认选择题模板",
        "description": "适用于各学科选择题生成",
        "template_text": (
            "请根据以下知识点生成 {count} 道{exercise_type}，难度等级 {difficulty}（1最简单，5最难）。\n\n"
            "【知识点】{kp_title}\n"
            "【描述】{kp_description}\n"
            "【所属章节】{chapter_title}\n\n"
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "题干", '
            '"options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}}, '
            '"answer": "B", "explanation": "解析", "difficulty": 3}}]}}\n\n'
            "要求：\n"
            "1. 每题必须有4个选项（A/B/C/D）\n"
            "2. 干扰项要有合理性，不能一眼看出错误\n"
            "3. 解析要清晰说明为什么选该答案\n"
            "4. 难度要符合指定等级\n"
            "5. 只输出 JSON，不要任何其他文字"
        ),
    },
    {
        "resource_type": "exercise_fill_blank",
        "name": "默认填空题模板",
        "description": "适用于各学科填空题生成",
        "template_text": (
            "请根据以下知识点生成 {count} 道{exercise_type}，难度等级 {difficulty}（1最简单，5最难）。\n\n"
            "【知识点】{kp_title}\n"
            "【描述】{kp_description}\n"
            "【所属章节】{chapter_title}\n\n"
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "题干（空白处用____表示）", '
            '"answer": "正确答案", "explanation": "解析", "difficulty": 3}}]}}\n\n'
            "要求：\n"
            "1. 题干中用 ____ 标注填空位置\n"
            "2. 每题只设一个空\n"
            "3. 答案要精确\n"
            "4. 只输出 JSON，不要任何其他文字"
        ),
    },
    {
        "resource_type": "exercise_short_answer",
        "name": "默认简答题模板",
        "description": "适用于各学科简答题生成",
        "template_text": (
            "请根据以下知识点生成 {count} 道{exercise_type}，难度等级 {difficulty}（1最简单，5最难）。\n\n"
            "【知识点】{kp_title}\n"
            "【描述】{kp_description}\n"
            "【所属章节】{chapter_title}\n\n"
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "题干", '
            '"answer": "参考答案", "key_points": ["要点1", "要点2"], '
            '"explanation": "解析", "difficulty": 3}}]}}\n\n'
            "要求：\n"
            "1. 题干表述清晰，问题明确\n"
            "2. 参考答案要完整\n"
            "3. 列出关键得分点(key_points)\n"
            "4. 只输出 JSON，不要任何其他文字"
        ),
    },
    {
        "resource_type": "exercise_true_false",
        "name": "默认判断题模板",
        "description": "适用于各学科判断题生成",
        "template_text": (
            "请根据以下知识点生成 {count} 道{exercise_type}，难度等级 {difficulty}（1最简单，5最难）。\n\n"
            "【知识点】{kp_title}\n"
            "【描述】{kp_description}\n"
            "【所属章节】{chapter_title}\n\n"
            "请以 JSON 格式输出，结构如下：\n"
            '{{"questions": [{{"id": 1, "stem": "判断题题干", '
            '"answer": true, "explanation": "解析", "difficulty": 3}}]}}\n\n'
            "要求：\n"
            "1. 正确和错误的题目比例大致均衡\n"
            "2. 错误的陈述要有迷惑性，不能太离谱\n"
            "3. answer 为布尔值 true 或 false\n"
            "4. 只输出 JSON，不要任何其他文字"
        ),
    },
]


async def seed_prompt_templates(session: AsyncSession):
    """插入默认 prompt 模板（如果不存在）"""
    for tpl_data in DEFAULT_PROMPTS:
        # 检查是否已存在
        stmt = select(PromptTemplate).where(
            PromptTemplate.resource_type == tpl_data["resource_type"],
            PromptTemplate.name == tpl_data["name"],
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            print(f"  [SKIP] Prompt '{tpl_data['name']}' already exists")
            continue

        tpl = PromptTemplate(
            resource_type=tpl_data["resource_type"],
            name=tpl_data["name"],
            description=tpl_data["description"],
            template_text=tpl_data["template_text"],
            is_active=True,
            version=1,
        )
        session.add(tpl)
        print(f"  [OK] Created prompt '{tpl_data['name']}'")

    await session.commit()


async def init_db():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        # 1. pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("[OK] pgvector extension enabled")

        # 2. business schemas
        for schema in ("content", "tutor", "learning"):
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            print(f"[OK] Schema '{schema}' created")

        # 3. create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("[OK] All tables created")

    # 4. seed data
    print("\n[SEED] Inserting default prompt templates...")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed_prompt_templates(session)

    await engine.dispose()
    print("\n[DONE] Database initialization complete!")


if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"\n[FAIL] {e}", file=sys.stderr)
        sys.exit(1)
