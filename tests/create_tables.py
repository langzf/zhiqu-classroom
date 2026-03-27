"""创建所有缺失的数据库 schema 和表"""
import asyncio
from sqlalchemy import text
from database import engine

# 导入所有模型，确保它们注册到 Base.metadata
from ai_tutor.models import Conversation, Message
from learning_core.models import LearningTask, MasteryRecord, StudySession
from user_profile.models import User, StudentProfile, GuardianBinding, UserOAuthBinding
from shared.base_model import Base

async def main():
    async with engine.begin() as conn:
        # 创建 schema
        for schema in ["tutor", "learning", "usr"]:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            print(f"Schema '{schema}' ensured")
        
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("All tables created!")
    
    # 验证
    async with engine.connect() as conn:
        for s in ["tutor", "learning", "usr"]:
            r = await conn.execute(text(
                f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{s}' ORDER BY table_name"
            ))
            tables = [row[0] for row in r.fetchall()]
            print(f"  {s}: {tables}")

asyncio.run(main())
