import asyncio, traceback
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        login = await c.post("/api/v1/auth/login", json={"phone": "13800009999"})
        token = login.json()["data"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        tests = [
            ("GET", "/api/v1/app/content/textbooks/00000000-0000-0000-0000-000000000000", None),
            ("GET", "/api/v1/app/learning/tasks/00000000-0000-0000-0000-000000000000", None),
            ("POST", "/api/v1/app/learning/tasks/00000000-0000-0000-0000-000000000000/start", None),
            ("POST", "/api/v1/app/learning/tasks/00000000-0000-0000-0000-000000000000/submit", {}),
        ]
        for method, url, body in tests:
            if method == "GET":
                r = await c.get(url, headers=h)
            else:
                r = await c.post(url, headers=h, json=body)
            short_url = url.replace("/api/v1", "")
            print(f"{method} {short_url} => {r.status_code}")
            try:
                data = r.json()
                print(f"  {data}")
            except Exception:
                print(f"  raw: {r.text[:500]}")
            print()

asyncio.run(main())
