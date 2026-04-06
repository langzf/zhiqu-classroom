"""Simulate alembic autogenerate diff to see what it detects."""
import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from infrastructure.persistence.models import Base

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    
    async with engine.connect() as conn:
        def do_compare(sync_conn):
            mc = MigrationContext.configure(
                sync_conn,
                opts={
                    "include_schemas": True,
                    "include_name": lambda name, type_, parent_names: name in {"public"} if type_ == "schema" else True,
                }
            )
            diff = compare_metadata(mc, Base.metadata)
            return diff
        
        diff = await conn.run_sync(do_compare)
        
        if not diff:
            print("No differences detected!")
        else:
            print(f"Found {len(diff)} differences:")
            for d in diff[:5]:
                print(f"  {d[0]}: {d[1] if len(d) > 1 else ''}")
                if len(d) > 2:
                    print(f"    detail: {d[2]}")
    
    await engine.dispose()

asyncio.run(main())
