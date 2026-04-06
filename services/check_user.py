import asyncio
from infrastructure.persistence.database import get_db_context
from sqlalchemy import text

async def check():
    async with get_db_context() as db:
        result = await db.execute(text("SELECT id, phone, role FROM users WHERE phone = '13800000001'"))
        rows = list(result)
        print(f"Found {len(rows)} rows:")
        for row in rows:
            print(f"  id={row[0]}, phone={row[1]}, role={row[2]}")

asyncio.run(check())
