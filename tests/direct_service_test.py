"""Direct service test — bypass HTTP, test TutorService.create_conversation."""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from ai_tutor.service import TutorService

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        svc = TutorService(session)
        try:
            conv = await svc.create_conversation(
                student_id="test-student-001",
                scene="free_chat",
                title="Direct test"
            )
            print(f"\nSUCCESS: conv.id={conv.id}, status={conv.status}")
        except Exception as e:
            print(f"\nERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.rollback()
    
    await engine.dispose()

asyncio.run(main())
