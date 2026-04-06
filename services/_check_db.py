import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables in DB ({len(tables)}):", tables)

        # Also check via SQLAlchemy inspect
        def sync_inspect(sync_conn):
            insp = inspect(sync_conn)
            return insp.get_table_names(schema="public")
        
        sa_tables = await conn.run_sync(sync_inspect)
        print(f"SA inspect ({len(sa_tables)}):", sorted(sa_tables))
    
    await engine.dispose()

asyncio.run(main())
