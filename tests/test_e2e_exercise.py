# -*- coding: utf-8 -*-
"""End-to-end exercise generation flow test"""
import sys, os, asyncio, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

import uuid6, jwt
from datetime import datetime, timezone, timedelta

# --- JWT ---
SECRET = "dev-secret-change-in-production"
now = datetime.now(timezone.utc)
payload = {
    "sub": "test-admin-001",
    "role": "admin",
    "exp": now + timedelta(hours=1),
    "iat": now,
    "jti": str(uuid6.uuid7()),
}
TOKEN = jwt.encode(payload, SECRET, algorithm="HS256")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BASE = "http://localhost:8001/api/v1/content"

import httpx

async def main():
    async with httpx.AsyncClient(timeout=60) as c:

        # STEP 1: Create textbook
        print("=== STEP 1: Create textbook ===")
        r = await c.post(f"{BASE}/textbooks", json={
            "title": "E2E Test Math",
            "subject": "math",
            "grade_range": "grade_7",
            "source_file_url": "http://minio:9000/zhiqu/test/placeholder.pdf",
        }, headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {d}")
            return
        tb_id = d["data"]["id"]
        print(f"  textbook_id: {tb_id}")

        # STEP 2: Insert chapter + KP via DB
        print("\n=== STEP 2: Insert chapter + KP ===")
        from sqlalchemy import text
        from database import engine as async_engine
        from sqlalchemy.ext.asyncio import AsyncSession

        ch_id = str(uuid6.uuid7())
        kp_id = str(uuid6.uuid7())

        async with AsyncSession(async_engine) as sess:
            await sess.execute(text("""
                INSERT INTO content.chapters (id, textbook_id, title, depth, sort_order)
                VALUES (:id, :tb_id, :title, 1, 1)
            """), {"id": ch_id, "tb_id": tb_id, "title": "Ch1 Rational Numbers"})

            await sess.execute(text("""
                INSERT INTO content.knowledge_points (id, chapter_id, title, difficulty)
                VALUES (:id, :ch_id, :title, 3)
            """), {"id": kp_id, "ch_id": ch_id, "title": "Addition of Rational Numbers"})

            await sess.commit()
        print(f"  chapter_id: {ch_id}")
        print(f"  kp_id: {kp_id}")

        # STEP 3: Get KP detail (was 500 before)
        print("\n=== STEP 3: GET knowledge-point detail ===")
        r = await c.get(f"{BASE}/knowledge-points/{kp_id}", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")
        else:
            print(f"  KP title: {d['data']['title']}")

        # STEP 4: Create prompt template
        print("\n=== STEP 4: Create prompt template ===")
        r = await c.post(f"{BASE}/prompts", json={
            "resource_type": "exercise_choice",
            "name": "Default Choice Template",
            "template_text": "Generate {count} multiple choice questions about {kp_title}",
            "description": "Test template",
            "is_active": True,
        }, headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")
        else:
            tpl_id = d["data"]["id"]
            print(f"  template_id: {tpl_id}")

        # STEP 5: List prompts (was 500 before)
        print("\n=== STEP 5: GET prompts list ===")
        r = await c.get(f"{BASE}/prompts?resource_type=exercise_choice", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")
        else:
            print(f"  Templates count: {len(d['data'])}")

        # STEP 6: Generate exercises (was 500 before)
        print("\n=== STEP 6: POST generate exercises ===")
        r = await c.post(f"{BASE}/exercises/generate", json={
            "knowledge_point_id": kp_id,
            "exercise_type": "choice",
            "count": 3,
            "difficulty": 3,
        }, headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")
        else:
            res = d["data"]
            print(f"  resource_id: {res['id']}")
            print(f"  resource_type: {res['resource_type']}")
            print(f"  title: {res['title']}")
            qs = res["content_json"].get("questions", [])
            print(f"  questions count: {len(qs)}")
            if qs:
                print(f"  first question: {qs[0].get('stem', '')[:80]}")

        # STEP 7: Get exercise by ID
        if d.get("code") == 0:
            rid = d["data"]["id"]
            print(f"\n=== STEP 7: GET exercise/{rid} ===")
            r = await c.get(f"{BASE}/exercises/{rid}", headers=HEADERS)
            print(f"  Status: {r.status_code}")
            d2 = r.json()
            print(f"  Code: {d2.get('code')}")

        # STEP 8: List exercises by KP
        print(f"\n=== STEP 8: GET kp/{kp_id}/exercises ===")
        r = await c.get(f"{BASE}/knowledge-points/{kp_id}/exercises", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d3 = r.json()
        print(f"  Code: {d3.get('code')}")
        if d3.get("code") == 0:
            print(f"  Exercises count: {len(d3['data'])}")

        print("\n=== DONE ===")

asyncio.run(main())
