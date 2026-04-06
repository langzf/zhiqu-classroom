"""Simulate alembic autogenerate diff - without include_schemas."""
import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import create_async_engine
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from infrastructure.persistence.models import Base

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    
    async with engine.connect() as conn:
        def do_compare(sync_conn):
            mc = MigrationContext.configure(sync_conn)
            diff = compare_metadata(mc, Base.metadata)
            return diff
        
        diff = await conn.run_sync(do_compare)
        
        if not diff:
            print("No differences detected!")
        else:
            print(f"Found {len(diff)} differences:")
            for d in diff[:5]:
                print(f"  {d}")
    
    await engine.dispose()

asyncio.run(main())
