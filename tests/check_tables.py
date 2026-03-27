"""Check learning schema tables."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('tutor', 'content', 'learning', 'usr') ORDER BY 1, 2"
        ))
        tables = [(row[0], row[1]) for row in result]
        print(f"All app tables ({len(tables)}):")
        for schema, tbl in tables:
            print(f"  {schema}.{tbl}")
    await engine.dispose()

asyncio.run(main())
