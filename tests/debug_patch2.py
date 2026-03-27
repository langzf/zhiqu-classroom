# -*- coding: utf-8 -*-
"""Debug PATCH with full error info"""
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
        # Create conversation
        r = await c.post(f"{BASE}/conversations", json={
            "scene": "homework_help",
            "title": "Debug Test",
        }, headers=HEADERS)
        d = r.json()
        print(f"Create code: {d.get('code')}")
        conv_id = d["data"]["id"]
        print(f"conv_id: {conv_id}")
        print(f"student_id in JWT: {student_id}")
        print(f"student_id in conv: {d['data']['student_id']}")

        # GET first
        r = await c.get(f"{BASE}/conversations/{conv_id}", headers=HEADERS)
        print(f"\nGET Status: {r.status_code}")
        print(f"GET Body: {r.text[:300]}")

        # PATCH
        r = await c.patch(f"{BASE}/conversations/{conv_id}", json={
            "title": "Updated Title"
        }, headers=HEADERS)
        print(f"\nPATCH Status: {r.status_code}")
        print(f"PATCH Headers: {dict(r.headers)}")
        print(f"PATCH Body: {r.text[:500]}")

asyncio.run(main())
