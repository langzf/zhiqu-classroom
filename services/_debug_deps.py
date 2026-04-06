import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    from httpx import AsyncClient, ASGITransport
    from main import app
    
    # Check what LearningSvc resolves to
    from interfaces.api.deps import get_learning_service
    import inspect
    
    # Also check the actual class
    from application.services.learning_service import LearningService
    print("LearningService methods:")
    for name in sorted(dir(LearningService)):
        if not name.startswith('_'):
            print(f"  {name}")
    
    print()
    print("Source file:", inspect.getfile(LearningService))
    
    # Check if there's a different class with same name
    print()
    print("get_learning_service source:", inspect.getsource(get_learning_service))

asyncio.run(main())
