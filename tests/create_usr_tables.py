"""Create user_profile tables in the 'usr' schema."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS usr.users (
    id UUID PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    nickname VARCHAR(100),
    avatar_url VARCHAR(500),
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    hashed_password VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS usr.parent_student (
    id UUID PRIMARY KEY,
    parent_id UUID NOT NULL REFERENCES usr.users(id),
    student_id UUID NOT NULL REFERENCES usr.users(id),
    relation VARCHAR(20) NOT NULL DEFAULT 'parent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(parent_id, student_id)
);

CREATE TABLE IF NOT EXISTS usr.login_logs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES usr.users(id),
    ip VARCHAR(50),
    device VARCHAR(200),
    logged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usr.user_settings (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES usr.users(id) UNIQUE,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu")
    async with engine.begin() as conn:
        for stmt in DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))
                tbl = stmt.split("usr.")[1].split()[0] if "usr." in stmt else "?"
                print(f"  Created: usr.{tbl}")
    
    # Verify
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='usr' ORDER BY 1"
        ))
        tables = [row[0] for row in result]
        print(f"\nusr tables: {tables}")
    
    await engine.dispose()

asyncio.run(main())
