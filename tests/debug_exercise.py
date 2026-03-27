# -*- coding: utf-8 -*-
"""Debug exercise generation - catch actual exception"""
import sys, os, asyncio, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

async def main():
    from database import engine as async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
    import uuid6

    # First find an existing KP
    async with AsyncSession(async_engine) as sess:
        r = await sess.execute(text("SELECT id, title FROM content.knowledge_points LIMIT 1"))
        row = r.first()
        if not row:
            print("No knowledge points found!")
            return
        kp_id = row[0]
        print(f"Using KP: {kp_id} ({row[1]})")

    # Now call generate_exercises directly
    async with AsyncSession(async_engine) as sess:
        try:
            from content_engine import exercise_service
            result = await exercise_service.generate_exercises(
                db=sess,
                kp_id=kp_id,
                exercise_type="choice",
                count=3,
                difficulty=3,
            )
            await sess.commit()
            print(f"SUCCESS: {result}")
        except Exception as e:
            print(f"EXCEPTION TYPE: {type(e).__name__}")
            print(f"EXCEPTION: {e}")
            traceback.print_exc()

asyncio.run(main())
