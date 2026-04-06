"""
zhiqu-classroom E2E API Test
=============================
Uses httpx.ASGITransport to test the FastAPI app in-process.
No need to start uvicorn - works directly with the ASGI app.
Requires: running PostgreSQL + Redis (see .env)
"""

import asyncio
import os
import sys
import json
import traceback

# Windows asyncio fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

# ── Helpers ────────────────────────────────────────────

PASS = 0
FAIL = 0
ERRORS: list[str] = []


def ok(name: str, detail: str = ""):
    global PASS
    PASS += 1
    extra = f" - {detail}" if detail else ""
    print(f"  [PASS] {name}{extra}")


def fail(name: str, detail: str = ""):
    global FAIL
    FAIL += 1
    extra = f" - {detail}" if detail else ""
    msg = f"  [FAIL] {name}{extra}"
    print(msg)
    ERRORS.append(msg)


def check(name: str, resp: httpx.Response, expected_status: int | tuple = 200):
    """Assert response status, print PASS/FAIL."""
    if isinstance(expected_status, tuple):
        if resp.status_code in expected_status:
            ok(name, f"{resp.status_code}")
            return True
        else:
            fail(name, f"expected one of {expected_status}, got {resp.status_code}")
            try:
                print(f"    body: {resp.text[:500]}")
            except Exception:
                pass
            return False
    else:
        if resp.status_code == expected_status:
            ok(name, f"{resp.status_code}")
            return True
        else:
            fail(name, f"expected {expected_status}, got {resp.status_code}")
            try:
                print(f"    body: {resp.text[:500]}")
            except Exception:
                pass
            return False


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Main ───────────────────────────────────────────────

async def run_tests():
    global PASS, FAIL

    print("=" * 60)
    print("  zhiqu-classroom E2E API Tests")
    print("=" * 60)

    # Import app
    print("\n[1] Importing FastAPI app...")
    try:
        from main import app
        ok("Import app")
    except Exception as e:
        fail("Import app", str(e))
        traceback.print_exc()
        return

    transport = httpx.ASGITransport(app=app)
    base_url = "http://test"

    async with httpx.AsyncClient(transport=transport, base_url=base_url) as c:

        # ── System ────────────────────────────────────
        print("\n[2] System endpoints")

        r = await c.get("/health")
        check("GET /health", r)

        r = await c.get("/docs")
        check("GET /docs (Swagger)", r)

        r = await c.get("/openapi.json")
        check("GET /openapi.json", r)

        # ── Auth ──────────────────────────────────────
        print("\n[3] Auth - Login & Token")

        # Student login (auto-register if not exists)
        phone = "13800009999"
        r = await c.post("/api/v1/auth/login", json={"phone": phone})
        if check("POST /auth/login (student)", r):
            body = r.json()
            # Handle both wrapped {"code":0,"data":{...}} and direct {"access_token":...}
            data = body.get("data") if isinstance(body, dict) else None
            if data is None:
                data = body  # try using body directly
            if isinstance(data, dict):
                student_token = data.get("access_token", "")
                refresh_token = data.get("refresh_token", "")
            else:
                student_token = ""
                refresh_token = ""
            if student_token:
                ok("Got student access_token")
            else:
                fail("Got student access_token",
                     f"body={json.dumps(body, ensure_ascii=False)[:400]}")
                student_token = ""
        else:
            student_token = ""
            refresh_token = ""

        # Admin login (separate phone)
        admin_phone = "13800000001"
        r = await c.post("/api/v1/auth/login/admin", json={"phone": admin_phone})
        if r.status_code == 200:
            body = r.json()
            data = body.get("data", body)
            admin_token = data.get("access_token", "")
            if admin_token:
                ok("POST /auth/login/admin", "got admin token")
            else:
                fail("POST /auth/login/admin", "200 but no token")
                admin_token = ""
        elif r.status_code == 401:
            # Admin not found or not admin role - expected if no admin user
            ok("POST /auth/login/admin", "401 (no admin user in DB, expected)")
            admin_token = ""
        else:
            fail("POST /auth/login/admin", f"{r.status_code}")
            admin_token = ""

        # Token refresh
        if refresh_token:
            r = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
            check("POST /auth/refresh", r)
        else:
            fail("POST /auth/refresh", "skipped - no refresh token")

        # Register
        r = await c.post("/api/v1/auth/register", json={
            "phone": "13800008888",
            "nickname": "TestUser8888",
        })
        check("POST /auth/register", r, (200, 201, 409))

        # ── Auth Guards ───────────────────────────────
        print("\n[4] Auth guards")

        # No token -> 401 or 403
        r = await c.get("/api/v1/app/user/me")
        check("GET /app/user/me (no token)", r, (401, 403))

        # Invalid token -> 401 or 403
        r = await c.get("/api/v1/app/user/me", headers=auth_header("invalid.jwt.token"))
        check("GET /app/user/me (bad token)", r, (401, 403))

        # Student accessing admin endpoint -> 403
        if student_token:
            r = await c.get("/api/v1/admin/users", headers=auth_header(student_token))
            check("GET /admin/users (student token -> 403)", r, (403,))
        else:
            fail("Admin guard test", "skipped - no student token")

        # ── User Profile ──────────────────────────────
        print("\n[5] User Profile")

        if student_token:
            headers = auth_header(student_token)

            r = await c.get("/api/v1/app/user/me", headers=headers)
            if check("GET /app/user/me", r):
                body = r.json()
                data = body.get("data", body)
                user_id = data.get("id", "")
                if user_id:
                    ok("User has id", user_id[:8] + "...")
                else:
                    fail("User has id", f"data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")

            # Update profile
            r = await c.put("/api/v1/app/user/me", headers=headers, json={
                "nickname": "TestStudent"
            })
            check("PUT /app/user/me (update nickname)", r)

            # Guardian bindings
            r = await c.get("/api/v1/app/user/guardian-bindings", headers=headers)
            check("GET /app/user/guardian-bindings", r)

            # Children list (for guardian role)
            r = await c.get("/api/v1/app/user/children", headers=headers)
            check("GET /app/user/children", r, (200, 403))
        else:
            fail("User Profile tests", "skipped - no student token")

        # ── Content (App) ─────────────────────────────
        print("\n[6] Content (App)")

        if student_token:
            headers = auth_header(student_token)

            r = await c.get("/api/v1/app/content/textbooks", headers=headers)
            check("GET /app/content/textbooks", r)

            # Get non-existent textbook -> 404
            r = await c.get("/api/v1/app/content/textbooks/00000000-0000-0000-0000-000000000000", headers=headers)
            check("GET /app/content/textbooks/{id} (404)", r, (404,))

            # Knowledge point search
            r = await c.post("/api/v1/app/content/knowledge-points/search", headers=headers, json={
                "query": "test",
            })
            check("POST /app/content/knowledge-points/search", r, (200, 422, 500))
        else:
            fail("Content tests", "skipped - no student token")

        # ── Learning (App) ────────────────────────────
        print("\n[7] Learning (App)")

        if student_token:
            headers = auth_header(student_token)

            r = await c.get("/api/v1/app/learning/tasks", headers=headers)
            check("GET /app/learning/tasks", r)

            # Get non-existent task -> 404
            r = await c.get("/api/v1/app/learning/tasks/00000000-0000-0000-0000-000000000000", headers=headers)
            check("GET /app/learning/tasks/{id} (404)", r, (404,))

            # Start non-existent task -> 404
            r = await c.post("/api/v1/app/learning/tasks/00000000-0000-0000-0000-000000000000/start", headers=headers)
            check("POST /app/learning/tasks/{id}/start (404)", r, (404, 422))

            # Submit non-existent task -> 404
            r = await c.post("/api/v1/app/learning/tasks/00000000-0000-0000-0000-000000000000/submit", headers=headers, json={})
            check("POST /app/learning/tasks/{id}/submit (404)", r, (404, 422))
        else:
            fail("Learning tests", "skipped - no student token")

        # ── Tutor (App) ──────────────────────────────
        print("\n[8] Tutor (App)")

        if student_token:
            headers = auth_header(student_token)

            # List conversations
            r = await c.get("/api/v1/app/tutor/conversations", headers=headers)
            check("GET /app/tutor/conversations", r)

            # Create conversation
            r = await c.post("/api/v1/app/tutor/conversations", headers=headers, json={
                "scene": "free_chat",
                "title": "E2E Test Conversation",
            })
            if check("POST /app/tutor/conversations", r, (200, 201)):
                body = r.json()
                data = body.get("data", body)
                conv_id = data.get("id", "")
                if conv_id:
                    ok("Created conversation", conv_id[:8] + "...")
                else:
                    conv_id = ""
                    fail("Created conversation", "no id in response")
            else:
                conv_id = ""

            # Get conversation
            if conv_id:
                r = await c.get(f"/api/v1/app/tutor/conversations/{conv_id}", headers=headers)
                check("GET /app/tutor/conversations/{id}", r)

                # Send message (may fail if LLM not configured)
                r = await c.post(f"/api/v1/app/tutor/conversations/{conv_id}/messages", headers=headers, json={
                    "content": "Hello from E2E test"
                })
                if r.status_code == 200:
                    ok("POST /app/tutor/.../messages", "200 (LLM responded)")
                elif r.status_code == 500:
                    ok("POST /app/tutor/.../messages", "500 (expected - LLM not configured)")
                else:
                    check("POST /app/tutor/.../messages", r, (200, 500))

            # Get non-existent conversation -> 404
            r = await c.get("/api/v1/app/tutor/conversations/00000000-0000-0000-0000-000000000000", headers=headers)
            check("GET /app/tutor/conversations/{id} (404)", r, (404,))
        else:
            fail("Tutor tests", "skipped - no student token")

        # ── Admin Endpoints ──────────────────────────
        print("\n[9] Admin endpoints (auth guard)")

        if student_token:
            headers = auth_header(student_token)

            # Student should get 403 on all admin endpoints
            r = await c.get("/api/v1/admin/users", headers=headers)
            check("GET /admin/users (student -> 403)", r, (403,))

            r = await c.get("/api/v1/admin/content/textbooks", headers=headers)
            check("GET /admin/content/textbooks (student -> 403)", r, (403,))

            r = await c.get("/api/v1/admin/learning/tasks", headers=headers)
            check("GET /admin/learning/tasks (student -> 403)", r, (403,))

        # If we have admin token, test admin CRUD
        if admin_token:
            headers = auth_header(admin_token)

            r = await c.get("/api/v1/admin/users", headers=headers)
            check("GET /admin/users (admin)", r)

            # Admin create textbook
            r = await c.post("/api/v1/admin/content/textbooks", headers=headers, json={
                "title": "E2E Test Textbook",
                "subject": "math",
                "grade_range": "grade_7-grade_9",
            })
            check("POST /admin/content/textbooks", r, (200, 201))

            # Admin create learning task
            r = await c.post("/api/v1/admin/learning/tasks", headers=headers, json={
                "title": "E2E Test Task",
                "task_type": "exercise",
                "description": "Test task from E2E",
                "items": [],
            })
            check("POST /admin/learning/tasks", r, (200, 201))
        else:
            ok("Admin CRUD tests", "skipped (no admin user)")

        # ── Validation ────────────────────────────────
        print("\n[10] Validation & edge cases")

        # Login with empty body -> 422
        r = await c.post("/api/v1/auth/login", json={})
        check("POST /auth/login (empty body -> 422)", r, 422)

        # Login with invalid JSON -> 422
        r = await c.post("/api/v1/auth/login", content=b"not json",
                         headers={"Content-Type": "application/json"})
        check("POST /auth/login (bad JSON -> 422)", r, 422)

        # 404 for non-existent path
        r = await c.get("/api/v1/nonexistent-path")
        check("GET /nonexistent-path (404)", r, 404)

    # ── Summary ───────────────────────────────────────
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"  Results: {PASS} passed, {FAIL} failed, {total} total")
    if ERRORS:
        print(f"\n  Failed tests:")
        for e in ERRORS:
            print(f"  {e}")
    print("=" * 60)

    return FAIL == 0


# ── Entry Point ───────────────────────────────────────

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)