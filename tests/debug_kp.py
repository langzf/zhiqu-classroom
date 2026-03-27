"""Quick debug: call the knowledge-point endpoint and show server traceback"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from database import engine, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def main():
    sm = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # 先找一个知识点 ID
    async with sm() as s:
        r = await s.execute(text("SELECT id, title FROM content.knowledge_points LIMIT 3"))
        rows = r.fetchall()
        print("Knowledge points in DB:")
        for row in rows:
            print(f"  {row[0]}  {row[1]}")
        
        if not rows:
            print("No knowledge points found!")
            return
        
        kp_id = str(rows[0][0])
    
    # 直接调用 service 层
    from content_engine.service import ContentService
    async with sm() as s:
        svc = ContentService(s)
        try:
            kp = await svc.get_knowledge_point(kp_id)
            print(f"\nService OK: {kp.title}")
        except Exception as e:
            print(f"\nService error: {e}")
            import traceback
            traceback.print_exc()
    
    # 测试 KnowledgePointOut
    from content_engine.schemas import KnowledgePointOut
    async with sm() as s:
        svc = ContentService(s)
        kp = await svc.get_knowledge_point(kp_id)
        try:
            out = KnowledgePointOut.model_validate(kp)
            print(f"\nSchema OK: {out.model_dump()}")
        except Exception as e:
            print(f"\nSchema error: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(main())
