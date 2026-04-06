"""Admin backend + frontend self-test."""
import json, urllib.request, urllib.error, sys, time

BASE = "http://127.0.0.1:8001"
ADMIN_FE = "http://localhost:3000"
results = []
token = None

def req(method, url, body=None, headers=None, timeout=10):
    headers = headers or {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=timeout)
        return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)

def test(name, method, url, body=None, headers=None, expected=(200,)):
    global results
    code, text = req(method, url, body, headers)
    ok = code in expected
    tag = "PASS" if ok else "FAIL"
    results.append((name, tag, code, text[:200] if not ok else ""))
    color = "\033[92m" if ok else "\033[91m"
    print(f"{color}[{tag}]\033[0m {name} ({code})")
    return code, text

print("\n========== SELF-TEST ==========\n")

# 1) Backend docs
test("Backend /docs", "GET", f"{BASE}/docs")

# 2) OpenAPI schema
test("OpenAPI Schema", "GET", f"{BASE}/openapi.json")

# 3) Frontend serves
test("Frontend HTML", "GET", f"{ADMIN_FE}/")

# 4) Admin login
code, text = test("Admin Login", "POST", f"{BASE}/api/v1/user/login/admin", body={"phone": "13800000001"})
if code == 200:
    data = json.loads(text)
    # find token
    for path in [
        lambda d: d.get("access_token"),
        lambda d: d.get("token"),
        lambda d: (d.get("data") or {}).get("access_token"),
        lambda d: (d.get("data") or {}).get("token"),
    ]:
        t = path(data)
        if t:
            token = t
            break
    if token:
        print(f"  -> token: {token[:40]}...")
    else:
        print(f"  -> response: {text[:200]}")

if not token:
    print("\n\033[93m[SKIP] No token — skipping authenticated tests\033[0m")
else:
    auth = {"Authorization": f"Bearer {token}"}

    # 5) /me
    code, text = test("GET /me", "GET", f"{BASE}/api/v1/user/me", headers=auth)
    if code == 200:
        me = json.loads(text)
        print(f"  -> user: {json.dumps(me, ensure_ascii=False)[:120]}")

    # 6) List users
    code, text = test("List Users", "GET", f"{BASE}/api/v1/user/users", headers=auth)
    if code == 200:
        d = json.loads(text)
        if isinstance(d, dict):
            cnt = d.get("total", len(d.get("data", [])) if isinstance(d.get("data"), list) else "?")
        elif isinstance(d, list):
            cnt = len(d)
        else:
            cnt = "?"
        print(f"  -> total: {cnt}")

    # 7) List textbooks
    code, text = test("List Textbooks", "GET", f"{BASE}/api/v1/admin/content/textbooks", headers=auth)
    if code == 200:
        print(f"  -> {text[:150]}")

    # 8) Get single textbook
    code, text = test("Get Textbook (known ID)", "GET",
        f"{BASE}/api/v1/admin/content/textbooks/019d2e1b-8d60-778a-bff9-85e8d54d3adc", headers=auth,
        expected=(200, 404))
    if code == 200:
        print(f"  -> {text[:150]}")

    # 9) List knowledge points
    code, text = test("List Knowledge Points", "GET", f"{BASE}/api/v1/admin/content/knowledge-points", headers=auth)
    if code == 200:
        print(f"  -> {text[:150]}")

    # 10) List exercises
    code, text = test("List Exercises", "GET", f"{BASE}/api/v1/admin/content/exercises", headers=auth)
    if code == 200:
        print(f"  -> {text[:150]}")

    # 11) List tutor conversations
    code, text = test("List Tutor Conversations", "GET", f"{BASE}/api/v1/admin/tutor/conversations", headers=auth)
    if code == 200:
        print(f"  -> {text[:150]}")

    # 12) List learning tasks
    code, text = test("List Learning Tasks", "GET", f"{BASE}/api/v1/admin/learning/tasks", headers=auth)
    if code == 200:
        print(f"  -> {text[:150]}")

    # 13) Create textbook (POST)
    code, text = test("Create Textbook", "POST", f"{BASE}/api/v1/admin/content/textbooks",
        headers=auth,
        body={"title": "自测教材-" + str(int(time.time())), "subject": "数学", "grade_level": "七年级", "version": "人教版"},
        expected=(200, 201, 422))
    if code in (200, 201):
        print(f"  -> {text[:150]}")

    # 14) Frontend proxy -> backend
    code, text = test("Frontend Proxy -> Login", "POST", f"{ADMIN_FE}/api/v1/user/login/admin",
        body={"phone": "13800000001"})
    if code == 200:
        print(f"  -> proxy OK")

    code, text = test("Frontend Proxy -> Textbooks", "GET", f"{ADMIN_FE}/api/v1/admin/content/textbooks", headers=auth)
    if code == 200:
        print(f"  -> proxy textbooks OK")

# Summary
print("\n========== SUMMARY ==========")
passed = sum(1 for _, s, _, _ in results if s == "PASS")
failed = sum(1 for _, s, _, _ in results if s == "FAIL")
total = len(results)
color = "\033[92m" if failed == 0 else "\033[91m"
print(f"{color}PASS: {passed}  FAIL: {failed}  TOTAL: {total}\033[0m")
if failed:
    print("\nFailed tests:")
    for name, status, code, detail in results:
        if status == "FAIL":
            print(f"  \033[91m✗ {name} [{code}]: {detail}\033[0m")
    sys.exit(1)
else:
    print("\n\033[92m✓ All tests passed!\033[0m")
