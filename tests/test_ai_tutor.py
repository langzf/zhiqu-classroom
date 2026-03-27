# -*- coding: utf-8 -*-
"""AI Tutor e2e test - conversation CRUD + message flow"""
import sys, os, asyncio, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

import uuid6, jwt, httpx
from datetime import datetime, timezone, timedelta

SECRET = "dev-secret-change-in-production"
now = datetime.now(timezone.utc)
student_id = str(uuid6.uuid7())
payload = {"sub": student_id, "role": "student", "exp": now + timedelta(hours=1), "iat": now, "jti": str(uuid6.uuid7())}
TOKEN = jwt.encode(payload, SECRET, algorithm="HS256")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BASE = "http://localhost:8001/api/v1/tutor"

async def main():
    async with httpx.AsyncClient(timeout=30) as c:

        # STEP 1: Create conversation
        print("=== STEP 1: Create conversation ===")
        r = await c.post(f"{BASE}/conversations", json={
            "scene": "homework_help",
            "title": "Math Homework Help",
            "context": {"subject": "math", "grade": 7}
        }, headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")
            return
        conv_id = d["data"]["id"]
        print(f"  conversation_id: {conv_id}")
        print(f"  student_id: {d['data']['student_id']}")
        print(f"  scene: {d['data']['scene']}")
        print(f"  status: {d['data']['status']}")

        # STEP 2: List conversations
        print("\n=== STEP 2: List conversations ===")
        r = await c.get(f"{BASE}/conversations", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") == 0:
            print(f"  Total: {d.get('total', len(d['data']))}")

        # STEP 3: Get conversation detail
        print(f"\n=== STEP 3: GET conversation/{conv_id} ===")
        r = await c.get(f"{BASE}/conversations/{conv_id}", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")

        # STEP 4: Send message (LLM will fail, but should degrade gracefully)
        print(f"\n=== STEP 4: Send message ===")
        r = await c.post(f"{BASE}/conversations/{conv_id}/messages", json={
            "content": "What is 2 + 3?"
        }, headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") != 0:
            print(f"  ERROR: {json.dumps(d, indent=2, ensure_ascii=False)}")
        else:
            data = d["data"]
            print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            if isinstance(data, dict) and "content" in data:
                print(f"  AI reply: {data['content'][:100]}")
            elif isinstance(data, dict) and "messages" in data:
                for m in data["messages"]:
                    print(f"    [{m['role']}] {m['content'][:80]}")
            elif isinstance(data, list):
                for m in data:
                    print(f"    [{m.get('role','')}] {m.get('content','')[:80]}")
            else:
                print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}")

        # STEP 5: Get message history
        print(f"\n=== STEP 5: GET messages ===")
        r = await c.get(f"{BASE}/conversations/{conv_id}/messages", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") == 0:
            print(f"  Messages count: {len(d['data'])}")
            for msg in d["data"]:
                print(f"    [{msg['role']}] {msg['content'][:60]}")

        # STEP 6: Update conversation
        print(f"\n=== STEP 6: PATCH conversation ===")
        r = await c.patch(f"{BASE}/conversations/{conv_id}", json={
            "title": "Updated: Math Help Session"
        }, headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")
        if d.get("code") == 0:
            print(f"  New title: {d['data']['title']}")

        # STEP 7: Archive conversation
        print(f"\n=== STEP 7: Archive conversation ===")
        r = await c.post(f"{BASE}/conversations/{conv_id}/archive", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")

        # STEP 8: Delete conversation
        print(f"\n=== STEP 8: DELETE conversation ===")
        r = await c.delete(f"{BASE}/conversations/{conv_id}", headers=HEADERS)
        print(f"  Status: {r.status_code}")
        d = r.json()
        print(f"  Code: {d.get('code')}")

        print("\n=== AI TUTOR TESTS DONE ===")

asyncio.run(main())
