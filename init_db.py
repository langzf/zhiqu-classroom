"""Create all tables and schemas from ORM models."""
import asyncio
import sys
import os

# Add services/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from infrastructure.persistence.models.base import Base
# Import all models to ensure they're registered with Base.metadata
from infrastructure.persistence.models import (
    user, content, learning, tutor
)


async def main():
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu"
    )
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        # Create schemas if not exist
        for schema in ("users", "content", "tutor", "learning"):
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        print("✅ Schemas ensured")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables created")

    await engine.dispose()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
