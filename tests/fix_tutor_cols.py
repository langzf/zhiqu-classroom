"""Add missing columns to tutor tables."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

ALTERS = [
    "ALTER TABLE tutor.conversations ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE tutor.conversations ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE tutor.conversations ADD COLUMN IF NOT EXISTS message_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE tutor.messages ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE tutor.messages ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0",
]

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    async with engine.begin() as conn:
        for stmt in ALTERS:
            try:
                await conn.execute(text(stmt))
                col = stmt.split("ADD COLUMN IF NOT EXISTS ")[1].split()[0]
                tbl = stmt.split("TABLE ")[1].split()[0]
                print(f"  OK: {tbl}.{col}")
            except Exception as e:
                print(f"  SKIP: {e}")
    
    # Verify
    async with engine.connect() as conn:
        for table in ["conversations", "messages"]:
            result = await conn.execute(text(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_schema='tutor' AND table_name='{table}' ORDER BY ordinal_position"
            ))
            cols = [(r[0], r[1]) for r in result]
            print(f"\ntutor.{table}: {[c[0] for c in cols]}")
    
    await engine.dispose()

asyncio.run(main())
