"""Check and create missing schemas/tables."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    
    async with engine.begin() as conn:
        # Check existing schemas
        result = await conn.execute(text("SELECT schema_name FROM information_schema.schemata ORDER BY 1"))
        schemas = [row[0] for row in result]
        print(f"Existing schemas: {schemas}")
        
        # Create missing schemas
        for s in ['tutor', 'content', 'learning', 'usr']:
            if s not in schemas:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {s}"))
                print(f"  Created schema: {s}")
        
        # Check all application tables
        result = await conn.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('tutor', 'content', 'learning', 'usr') ORDER BY 1, 2"
        ))
        tables = [(row[0], row[1]) for row in result]
        print(f"\nApplication tables ({len(tables)}):")
        for schema, tbl in tables:
            print(f"  {schema}.{tbl}")
    
    await engine.dispose()

asyncio.run(main())
