"""Check chapter table columns"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from database import engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def main():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        for table in ("chapters", "knowledge_points", "generated_resources"):
            r = await s.execute(text(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_schema='content' AND table_name='{table}' "
                f"ORDER BY ordinal_position"
            ))
            print(f"\n--- {table} ---")
            for row in r.fetchall():
                print(f"  {row[0]:30s} {row[1]}")

asyncio.run(main())
