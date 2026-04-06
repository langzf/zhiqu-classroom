import asyncio
from infrastructure.persistence.database import get_db_context
from sqlalchemy import text

async def check():
    async with get_db_context() as db:
        # 检查所有 schema
        result = await db.execute(text("SELECT schema_name FROM information_schema.schemata"))
        schemas = [row[0] for row in result]
        print(f"Available schemas: {schemas}")
        
        # 检查 users 表在哪个 schema
        result = await db.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name = 'users'
        """))
        tables = list(result)
        print(f"\nTables named 'users': {tables}")
        
        # 尝试查询 public.users
        result = await db.execute(text("SELECT id, phone, role FROM public.users WHERE phone = '13800000001'"))
        rows = list(result)
        print(f"\nFound {len(rows)} rows in public.users:")
        for row in rows:
            print(f"  id={row[0]}, phone={row[1]}, role={row[2]}")

asyncio.run(check())
