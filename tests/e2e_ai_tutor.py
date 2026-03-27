"""AI Tutor e2e test — all 8 steps"""
import json, sys, time, os, uuid
os.environ["PYTHONIOENCODING"] = "utf-8"
import jwt, requests

BASE = "http://localhost:8002"
SECRET = "dev-secret-change-in-production"
# Fixed UUID for test student (DB column is UUID type)
TEST_STUDENT_ID = "01965a00-0000-7000-8000-000000000001"

def make_token(sub=TEST_STUDENT_ID, role="student"):
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "exp": now + 3600,
        "iat": now,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

TOKEN = make_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def step(n, desc):
    print(f"\n{'='*50}\nSTEP {n}: {desc}\n{'='*50}")

def check(resp, expected_code=200, label=""):
    if resp.status_code != expected_code:
        print(f"  FAIL {label} -- expected {expected_code}, got {resp.status_code}")
        try:
            print(f"    body: {json.dumps(resp.json(), ensure_ascii=False)[:500]}")
        except:
            print(f"    body: {resp.text[:500]}")
        return False
    print(f"  OK {label} -- {resp.status_code}")
    return True

errors = []

# STEP 1: Create conversation
step(1, "Create conversation")
r = requests.post(f"{BASE}/api/v1/tutor/conversations",
                  headers=HEADERS,
                  json={"scene": "free_chat", "title": "E2E test session"})
if not check(r, 200, "POST /conversations"):
    errors.append("STEP1")
    print("FATAL: cannot continue without conversation")
    sys.exit(1)
data = r.json()["data"]
CONV_ID = data["id"]
print(f"  conv_id: {CONV_ID}")
print(f"  status: {data.get('status')}, scene: {data.get('scene')}")

# STEP 2: List conversations
step(2, "List conversations")
r = requests.get(f"{BASE}/api/v1/tutor/conversations",
                 headers=HEADERS, params={"status": "active"})
if not check(r, 200, "GET /conversations"):
    errors.append("STEP2")
else:
    body = r.json()["data"]
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        items = body.get("items", [])
    else:
        items = []
    print(f"  count: {len(items)}")

# STEP 3: Get single conversation
step(3, "Get conversation detail")
r = requests.get(f"{BASE}/api/v1/tutor/conversations/{CONV_ID}",
                 headers=HEADERS)
if not check(r, 200, f"GET /conversations/{CONV_ID}"):
    errors.append("STEP3")
else:
    print(f"  title: {r.json()['data'].get('title')}")

# STEP 4: Send message
step(4, "Send message")
r = requests.post(f"{BASE}/api/v1/tutor/conversations/{CONV_ID}/messages",
                  headers=HEADERS,
                  json={"content": "Hello, explain photosynthesis please."})
MSG_ID = None
if not check(r, 200, "POST /messages"):
    errors.append("STEP4")
else:
    msg_data = r.json()["data"]
    if "user_message" in msg_data:
        user_msg = msg_data["user_message"]
        asst_msg = msg_data["assistant_message"]
        MSG_ID = asst_msg["id"]
        print(f"  user_msg_id: {user_msg['id']}")
        print(f"  asst_msg_id: {MSG_ID}")
        print(f"  reply: {str(asst_msg.get('content', ''))[:80]}")
    elif "messages" in msg_data:
        msgs = msg_data["messages"]
        MSG_ID = msgs[-1]["id"]
        print(f"  messages: {len(msgs)}")
    elif "id" in msg_data:
        MSG_ID = msg_data["id"]
        print(f"  msg_id: {MSG_ID}")
    else:
        print(f"  unknown format: {list(msg_data.keys())}")

# STEP 5: List messages
step(5, "List messages")
r = requests.get(f"{BASE}/api/v1/tutor/conversations/{CONV_ID}/messages",
                 headers=HEADERS)
if not check(r, 200, "GET /messages"):
    errors.append("STEP5")
else:
    msg_body = r.json()["data"]
    if isinstance(msg_body, list):
        msg_items = msg_body
    elif isinstance(msg_body, dict):
        msg_items = msg_body.get("items", msg_body.get("messages", []))
    else:
        msg_items = []
    count = len(msg_items) if isinstance(msg_items, list) else "?"
    print(f"  message_count: {count}")

# STEP 6: Update conversation (PATCH)
step(6, "Update conversation (PATCH)")
r = requests.patch(f"{BASE}/api/v1/tutor/conversations/{CONV_ID}",
                   headers=HEADERS,
                   json={"title": "E2E test - updated title"})
if not check(r, 200, "PATCH /conversations"):
    errors.append("STEP6")
else:
    print(f"  new title: {r.json()['data'].get('title')}")

# STEP 7: Archive conversation
step(7, "Archive conversation")
r = requests.post(f"{BASE}/api/v1/tutor/conversations/{CONV_ID}/archive",
                  headers=HEADERS)
if not check(r, 200, "POST /archive"):
    # fallback: try PATCH status
    print("  -> trying PATCH status=archived ...")
    r2 = requests.patch(f"{BASE}/api/v1/tutor/conversations/{CONV_ID}",
                        headers=HEADERS,
                        json={"status": "archived"})
    if not check(r2, 200, "PATCH status=archived"):
        errors.append("STEP7")
    else:
        print(f"  status: {r2.json()['data'].get('status')}")
else:
    print(f"  status: {r.json()['data'].get('status')}")

# STEP 8: Message feedback
step(8, "Message feedback")
if MSG_ID:
    r = requests.post(f"{BASE}/api/v1/tutor/messages/{MSG_ID}/feedback",
                      headers=HEADERS,
                      json={"rating": 5, "comment": "Great reply!"})
    if not check(r, 200, "POST /feedback"):
        errors.append("STEP8")
    else:
        print(f"  feedback submitted")
else:
    print("  SKIP: no message ID")
    errors.append("STEP8-skip")

# Summary
print(f"\n{'='*50}")
if errors:
    print(f"FAILED steps: {errors}")
    sys.exit(1)
else:
    print("ALL 8 STEPS PASSED!")
    sys.exit(0)
