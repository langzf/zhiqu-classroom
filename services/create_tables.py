"""Create all missing database tables from ORM models."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.persistence.database import engine
from infrastructure.persistence.models import Base  # imports all models


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
