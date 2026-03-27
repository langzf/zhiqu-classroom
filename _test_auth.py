"""Auth API complete e2e test"""
import sys
sys.path.insert(0, "services")

import asyncio
import httpx
import json
import time

BASE = "http://localhost:8002/api/v1/user"
# Use unique phone for each run
PHONE = f"139{int(time.time()) % 100000000:08d}"
NICKNAME = "E2ETestUser"

async def main():
    async with httpx.AsyncClient(timeout=15) as c:
        results = []

        # ── 1. Register new user ──
        print(f"=== STEP 1: Register (phone={PHONE}) ===")
        r = await c.post(f"{BASE}/register", json={
            "phone": PHONE,
            "nickname": NICKNAME,
            "role": "student",
        })
        print(f"  Status: {r.status_code}")
        body = r.json()
        print(f"  Body: {json.dumps(body, indent=2, ensure_ascii=False)[:400]}")
        ok1 = r.status_code == 200 and body.get("code") == 0
        results.append(("register", "OK" if ok1 else f"FAIL {r.status_code}"))

        user_id = body.get("data", {}).get("id") if ok1 else None

        # ── 2. Duplicate register ──
        print("\n=== STEP 2: Duplicate Register ===")
        r = await c.post(f"{BASE}/register", json={
            "phone": PHONE,
            "nickname": "Dup",
            "role": "student",
        })
        print(f"  Status: {r.status_code}")
        results.append(("duplicate_register", "OK" if r.status_code == 422 else f"FAIL {r.status_code}"))

        # ── 3. Login ──
        print("\n=== STEP 3: Login ===")
        r = await c.post(f"{BASE}/login", json={"phone": PHONE})
        print(f"  Status: {r.status_code}")
        body = r.json()
        data = body.get("data", {})
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        login_user = data.get("user", {})
        print(f"  Has access_token: {bool(access_token)}")
        print(f"  Has refresh_token: {bool(refresh_token)}")
        print(f"  User nickname: {login_user.get('nickname')}")
        results.append(("login", "OK" if access_token and refresh_token else f"FAIL {r.status_code}"))

        if not access_token:
            print("\nNo token, stopping.")
            print_summary(results)
            return

        headers = {"Authorization": f"Bearer {access_token}"}

        # ── 4. Get Profile ──
        print("\n=== STEP 4: GET /me ===")
        r = await c.get(f"{BASE}/me", headers=headers)
        print(f"  Status: {r.status_code}")
        body = r.json()
        print(f"  Nickname: {body.get('data', {}).get('nickname')}")
        results.append(("get_profile", "OK" if r.status_code == 200 else f"FAIL {r.status_code}"))

        # ── 5. Update Profile ──
        print("\n=== STEP 5: PATCH /me ===")
        r = await c.patch(f"{BASE}/me", headers=headers, json={
            "nickname": "UpdatedName",
        })
        print(f"  Status: {r.status_code}")
        body = r.json()
        updated_name = body.get("data", {}).get("nickname")
        print(f"  New nickname: {updated_name}")
        ok5 = r.status_code == 200 and updated_name == "UpdatedName"
        results.append(("update_profile", "OK" if ok5 else f"FAIL {r.status_code}"))

        # ── 6. Refresh Token ──
        print("\n=== STEP 6: POST /refresh ===")
        r = await c.post(f"{BASE}/refresh", json={"refresh_token": refresh_token})
        print(f"  Status: {r.status_code}")
        body = r.json()
        new_access = body.get("data", {}).get("access_token")
        print(f"  New access_token: {bool(new_access)}")
        results.append(("refresh_token", "OK" if r.status_code == 200 and new_access else f"FAIL {r.status_code}"))

        # Verify new token works
        if new_access:
            r = await c.get(f"{BASE}/me", headers={"Authorization": f"Bearer {new_access}"})
            results.append(("refreshed_token_works", "OK" if r.status_code == 200 else f"FAIL {r.status_code}"))

        # ── 7. Invalid Token ──
        print("\n=== STEP 7: Invalid Token ===")
        r = await c.get(f"{BASE}/me", headers={"Authorization": "Bearer bad.token"})
        print(f"  Status: {r.status_code}")
        results.append(("invalid_token_rejected", "OK" if r.status_code in (401, 403) else f"FAIL {r.status_code}"))

        # ── 8. No Token ──
        print("\n=== STEP 8: No Token ===")
        r = await c.get(f"{BASE}/me")
        print(f"  Status: {r.status_code}")
        results.append(("no_token_rejected", "OK" if r.status_code in (401, 403, 422) else f"FAIL {r.status_code}"))

        # ── 9. Login non-existent user ──
        print("\n=== STEP 9: Login non-existent user ===")
        r = await c.post(f"{BASE}/login", json={"phone": "10000000000"})
        print(f"  Status: {r.status_code}")
        results.append(("login_nonexistent", "OK" if r.status_code in (404, 422) else f"FAIL {r.status_code}"))

        print_summary(results)


def print_summary(results):
    print("\n" + "=" * 50)
    print("AUTH API TEST SUMMARY")
    print("=" * 50)
    ok_count = 0
    fail_count = 0
    for name, status in results:
        if status.startswith("OK"):
            icon = "[PASS]"
            ok_count += 1
        elif "SKIP" in status:
            icon = "[SKIP]"
        else:
            icon = "[FAIL]"
            fail_count += 1
        print(f"  {icon} {name}: {status}")
    
    print(f"\n  >> {ok_count} passed, {fail_count} failed")
    if fail_count == 0:
        print("  >> ALL TESTS PASSED!")


asyncio.run(main())
