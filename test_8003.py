import httpx

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTlkMzMyYi05Y2QxLTc1NWEtYWM5Yi0yZTllMWI2YmU2NDAiLCJyb2xlIjoiYWRtaW4iLCJpYXQiOjE3NzUwNDIwNDAsImV4cCI6MTc3NTEyODQ0MCwianRpIjoiMDE5ZDQ4YzAtMTEyOS03NzcxLTgyYTgtNWRjZTkzNjVkYzIyIn0.7ZcflAezeABXGh1AGvMQAF3D-X0CZ5Dy7cn8jIX5q4o"
headers = {"Authorization": f"Bearer {token}"}
base = "http://localhost:8003"

print("=== Testing tutor conversations ===")
r1 = httpx.get(f"{base}/api/v1/admin/tutor/conversations?page=1&page_size=20", headers=headers)
print(f"Status: {r1.status_code}")
print(f"Response: {r1.text[:500]}\n")

print("=== Testing textbooks ===")
r2 = httpx.get(f"{base}/api/v1/admin/content/textbooks", headers=headers)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:500]}")
