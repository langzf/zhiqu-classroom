# -*- coding: utf-8 -*-
"""Debug update_conversation"""
import sys, os, asyncio, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

async def main():
    from sqlalchemy.ext.asyncio import AsyncSession
    from database import engine as async_engine
    from ai_tutor.service import TutorService

    # First create a conversation
    async with AsyncSession(async_engine) as sess:
        svc = TutorService(sess)
        conv = await svc.create_conversation(
            student_id="test-debug-001",
            scene="homework_help",
            title="Debug Conv",
        )
        await sess.commit()
        conv_id = str(conv.id)
        print(f"Created: {conv_id}")

    # Now try to update
    async with AsyncSession(async_engine) as sess:
        svc = TutorService(sess)
        try:
            updated = await svc.update_conversation(conv_id, title="Updated Title")
            await sess.commit()
            print(f"Updated: {updated.title}")
        except Exception as e:
            print(f"EXCEPTION TYPE: {type(e).__name__}")
            print(f"EXCEPTION: {e}")
            traceback.print_exc()

asyncio.run(main())
