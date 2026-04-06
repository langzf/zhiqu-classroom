import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id, phone, nickname, role, is_active FROM users WHERE role='admin'"))
        rows = r.fetchall()
        if rows:
            for row in rows:
                print(f"id={row[0]} phone={row[1]} nickname={row[2]} role={row[3]} active={row[4]}")
        else:
            print("No admin users found")
    await engine.dispose()

asyncio.run(main())
