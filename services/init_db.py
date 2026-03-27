"""
初始化数据库 — 创建 schema、启用扩展、建表
用法: python init_db.py
"""

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import get_settings

# ── 导入所有 models 使其注册到 Base.metadata ──
from shared.base_model import Base
import user_profile.models  # noqa: F401
import content_engine.models  # noqa: F401
import ai_tutor.models  # noqa: F401
import learning_orchestrator.models  # noqa: F401


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

    await engine.dispose()
    print("\n[DONE] Database initialization complete!")


if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"\n[FAIL] {e}", file=sys.stderr)
        sys.exit(1)
