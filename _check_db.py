"""Quick DB check script"""
import sys
sys.path.insert(0, "services")

import asyncio
from database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as c:
        r = await c.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        tables = [row[0] for row in r.fetchall()]
        print(f"Tables ({len(tables)}): {tables}")

        # Check alembic version
        r2 = await c.execute(text(
            "SELECT version_num FROM alembic_version"
        ))
        versions = [row[0] for row in r2.fetchall()]
        print(f"Alembic versions: {versions}")
    await engine.dispose()

asyncio.run(check())
