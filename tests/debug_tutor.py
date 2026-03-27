# -*- coding: utf-8 -*-
"""Debug AI Tutor list_conversations"""
import sys, os, asyncio, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

async def main():
    from sqlalchemy.ext.asyncio import AsyncSession
    from database import engine as async_engine
    from ai_tutor.service import TutorService

    async with AsyncSession(async_engine) as sess:
        svc = TutorService(sess)
        try:
            # Just list conversations for a test user
            convs, total = await svc.list_conversations(student_id="test-admin-001")
            print(f"Total: {total}")
            for c in convs:
                print(f"  {c.id} | {c.title} | {c.status}")
        except Exception as e:
            print(f"EXCEPTION TYPE: {type(e).__name__}")
            print(f"EXCEPTION: {e}")
            traceback.print_exc()

asyncio.run(main())
