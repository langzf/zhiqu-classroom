"""Quick test: just create a conversation and print full response."""
import time, uuid, jwt, requests, json

BASE = "http://localhost:8002"
SECRET = "dev-secret-change-in-production"
now = int(time.time())
token = jwt.encode({"sub": "test-student-001", "role": "student", "exp": now + 3600, "iat": now, "jti": str(uuid.uuid4())}, SECRET, algorithm="HS256")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Test 1: health
r = requests.get(f"{BASE}/health")
print(f"Health: {r.status_code} {r.text}")

# Test 2: create conversation
r = requests.post(f"{BASE}/api/v1/tutor/conversations", headers=headers,
                  json={"scene": "free_chat", "title": "test"})
print(f"\nCreate conv: {r.status_code}")
print(json.dumps(r.json(), indent=2, ensure_ascii=False, default=str))
