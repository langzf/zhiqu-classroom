"""Quick project status check."""
import asyncio
import asyncpg
import httpx

DB_URL = "postgresql://postgres:postgres@localhost:5432/zhiqu"

async def check_db():
    print("=== DATABASE TABLES ===")
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch(
        "SELECT schemaname, tablename FROM pg_tables "
        "WHERE schemaname IN ('content','tutor','learning','usr') "
        "ORDER BY schemaname, tablename"
    )
    for r in rows:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema=$1 AND table_name=$2 ORDER BY ordinal_position",
            r['schemaname'], r['tablename']
        )
        col_names = [c['column_name'] for c in cols]
        print(f"  {r['schemaname']}.{r['tablename']} ({len(col_names)} cols): {', '.join(col_names)}")
    await conn.close()

async def check_server():
    print("\n=== SERVER STATUS ===")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:8002/health")
            print(f"  Health: {r.status_code} {r.json()}")
            
            r2 = await client.get("http://localhost:8002/openapi.json")
            if r2.status_code == 200:
                paths = list(r2.json().get("paths", {}).keys())
                print(f"  Registered endpoints ({len(paths)}):")
                for p in sorted(paths):
                    methods = list(r2.json()["paths"][p].keys())
                    print(f"    {', '.join(m.upper() for m in methods)} {p}")
    except Exception as e:
        print(f"  Server not reachable: {e}")

async def main():
    await check_db()
    await check_server()

asyncio.run(main())
