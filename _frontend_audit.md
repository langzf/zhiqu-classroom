# Frontend API Audit — 2026-03-31

## Route Mounting (from __init__.py + main.py)
- `/api/v1` is the top prefix
- Auth: `/api/v1/auth` (prefix="/auth")
- App User: `/api/v1/app/user` (prefix="/app/user")
- App Content: `/api/v1/app/content` (prefix="/app/content")
- App Learning: `/api/v1/app/learning` (prefix="/app/learning")
- App Tutor: `/api/v1/app/tutor` (prefix="/app/tutor")
- Admin User: `/api/v1/admin/users` (prefix="/admin/users")
- Admin Content: `/api/v1/admin/content` (prefix="/admin/content")
- Admin Learning: `/api/v1/admin/learning` (prefix="/admin/learning")

## Client BaseURLs
- App: baseURL = `/api/v1`
- Admin: baseURL = `/api/v1`

## Vite Proxy
- App: proxy `/api` → `http://localhost:8000`
- Admin: proxy `/api` → `http://localhost:8000`

---

## APP FRONTEND — user.ts
| Frontend Call | Backend Endpoint | Status |
|---|---|---|
| `POST /auth/login` | `POST /auth/login` ✅ | OK |
| `POST /auth/register` | `POST /auth/register` ✅ | OK |
| `POST /auth/send-code` | ❌ 不存在 | ⚠️ 前端有调用但后端无端点 |
| `POST /auth/refresh` | `POST /auth/refresh` ✅ | OK |
| `GET /app/user/me` | `GET /app/user/me` ✅ | OK |
| `PUT /app/user/me` | `PATCH /app/user/me` | ❌ HTTP 方法不匹配 |
| `POST /app/user/guardian-bindings` | `POST /app/user/guardian-bindings` ✅ | OK |
| `GET /app/user/children` | `GET /app/user/children` ✅ | OK |

## APP FRONTEND — content.ts
需要对照检查路径

## APP FRONTEND — learning.ts
需要对照检查路径

## APP FRONTEND — tutor.ts
需要对照检查路径

## ADMIN FRONTEND — user.ts
需要对照检查

## ADMIN FRONTEND — content.ts
需要对照检查

## ADMIN FRONTEND — learning.ts
需要对照检查
