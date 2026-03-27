"""Debug the 3 failing endpoints - round 2"""
import asyncio, sys, os, traceback, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def main():
    sm = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # 找知识点
    async with sm() as s:
        r = await s.execute(text("SELECT id, chapter_id, title FROM content.knowledge_points ORDER BY created_at DESC LIMIT 1"))
        row = r.fetchone()
        if not row:
            print("No KP found")
            return
        kp_id = row[0]  # UUID object
        print(f"KP: {kp_id} | {row[2]}")
    
    # Test 1: KnowledgePointOut - SHOULD PASS NOW
    print("\n--- Test 1: KnowledgePointOut ---")
    from content_engine.service import ContentService
    from content_engine.schemas import KnowledgePointOut
    async with sm() as s:
        svc = ContentService(s)
        try:
            kp = await svc.get_knowledge_point(str(kp_id))
            out = KnowledgePointOut.model_validate(kp)
            print(f"  OK: {out.title}")
        except Exception:
            traceback.print_exc()
    
    # Test 2: list_prompt_templates - SHOULD PASS NOW
    print("\n--- Test 2: list_prompt_templates ---")
    from content_engine.prompt_service import list_prompt_templates
    async with sm() as s:
        try:
            templates = await list_prompt_templates(s, resource_type="exercise_choice")
            print(f"  Got {len(templates)} templates")
            if templates:
                from content_engine.schemas import PromptTemplateOut
                out = PromptTemplateOut.model_validate(templates[0])
                print(f"  OK: {out.name}")
        except Exception:
            traceback.print_exc()
    
    # Test 3: generate_exercises with correct kwargs
    print("\n--- Test 3: generate_exercises ---")
    from content_engine.exercise_service import generate_exercises
    async with sm() as s:
        try:
            result = await generate_exercises(
                s,
                kp_id=kp_id,
                exercise_type="choice",
                count=2,
                difficulty=3,
            )
            print(f"  Generated: {result.title}")
        except Exception:
            traceback.print_exc()

asyncio.run(main())
