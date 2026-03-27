"""Check tutor.conversations columns."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    async with engine.connect() as conn:
        for table in ["conversations", "messages"]:
            result = await conn.execute(text(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_schema='tutor' AND table_name='{table}' ORDER BY ordinal_position"
            ))
            cols = [(r[0], r[1], r[2]) for r in result]
            print(f"\ntutor.{table} ({len(cols)} columns):")
            for name, dtype, nullable in cols:
                print(f"  {name}: {dtype} {'NULL' if nullable == 'YES' else 'NOT NULL'}")
    await engine.dispose()

asyncio.run(main())
