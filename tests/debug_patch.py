# -*- coding: utf-8 -*-
"""Debug PATCH conversation"""
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
        conv_id = d["data"]["id"]
        print(f"Created: {conv_id}")

        # Try PATCH
        r = await c.patch(f"{BASE}/conversations/{conv_id}", json={
            "title": "Updated Title"
        }, headers=HEADERS)
        print(f"PATCH Status: {r.status_code}")
        print(f"PATCH Body: {r.text[:500]}")

asyncio.run(main())
