# 知趣课堂 - 前后端路由映射检查报告

## main.py 路由挂载配置

| 变量 | 来源模块 | mount prefix |
|---|---|---|
| `user_router` | `user_profile.router` | （无，router 自带 `/api/v1/user`）|
| `content_admin` | `content_engine.router_admin` | `/api/v1/admin` |
| `content_student` | `content_engine.router_student` | `/api/v1` |
| `tutor_admin` | `ai_tutor.router_admin` | `/api/v1/admin` |
| `tutor_student` | `ai_tutor.router_student` | `/api/v1` |
| `learning_admin` | `learning_orchestrator.router_admin` | `/api/v1/admin` |
| `learning_student` | `learning_orchestrator.router_student` | `/api/v1` |

## 后端完整路由表

### user_profile/router.py (router prefix = `/api/v1/user`, mount = 无)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | POST | `/api/v1/user/register` |
| 2 | POST | `/api/v1/user/login` |
| 3 | POST | `/api/v1/user/login/admin` |
| 4 | POST | `/api/v1/user/refresh` |
| 5 | GET | `/api/v1/user/me` |
| 6 | PATCH | `/api/v1/user/me` |
| 7 | POST | `/api/v1/user/me/guardian` |
| 8 | GET | `/api/v1/user/me/guardian` |
| 9 | GET | `/api/v1/user/admin/users` |
| 10 | GET | `/api/v1/user/admin/users/{user_id}` |
| 11 | PATCH | `/api/v1/user/admin/users/{user_id}` |

### content_engine/router_student.py (router prefix = `/content`, mount = `/api/v1`)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | GET | `/api/v1/content/textbooks` |
| 2 | GET | `/api/v1/content/textbooks/{textbook_id}` |
| 3 | GET | `/api/v1/content/textbooks/{textbook_id}/chapters` |
| 4 | GET | `/api/v1/content/knowledge-points` |
| 5 | POST | `/api/v1/content/knowledge-points/search` |

### content_engine/router_admin.py (router prefix = `/content`, mount = `/api/v1/admin`)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | GET | `/api/v1/admin/content/textbooks` |
| 2 | POST | `/api/v1/admin/content/textbooks` |
| 3 | POST | `/api/v1/admin/content/textbooks/upload` |
| 4 | GET | `/api/v1/admin/content/textbooks/{textbook_id}` |
| 5 | PUT | `/api/v1/admin/content/textbooks/{textbook_id}` |
| 6 | DELETE | `/api/v1/admin/content/textbooks/{textbook_id}` |
| 7 | POST | `/api/v1/admin/content/textbooks/{textbook_id}/parse` |
| 8 | GET | `/api/v1/admin/content/textbooks/{textbook_id}/chapters` |
| 9 | GET | `/api/v1/admin/content/knowledge-points` |
| 10 | POST | `/api/v1/admin/content/knowledge-points` |
| 11 | GET | `/api/v1/admin/content/knowledge-points/{kp_id}` |
| 12 | PUT | `/api/v1/admin/content/knowledge-points/{kp_id}` |
| 13 | DELETE | `/api/v1/admin/content/knowledge-points/{kp_id}` |
| 14 | POST | `/api/v1/admin/content/knowledge-points/search` |
| 15 | GET | `/api/v1/admin/content/exercises` |
| 16 | POST | `/api/v1/admin/content/exercises` |
| 17 | GET | `/api/v1/admin/content/exercises/{exercise_id}` |
| 18 | PUT | `/api/v1/admin/content/exercises/{exercise_id}` |
| 19 | DELETE | `/api/v1/admin/content/exercises/{exercise_id}` |

### ai_tutor/router_student.py (router prefix = `/tutor`, mount = `/api/v1`)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | POST | `/api/v1/tutor/conversations` |
| 2 | GET | `/api/v1/tutor/conversations` |
| 3 | GET | `/api/v1/tutor/conversations/{conversation_id}` |
| 4 | DELETE | `/api/v1/tutor/conversations/{conversation_id}` |
| 5 | POST | `/api/v1/tutor/conversations/{conversation_id}/messages` |
| 6 | GET | `/api/v1/tutor/conversations/{conversation_id}/messages` |
| 7 | POST | `/api/v1/tutor/conversations/{conversation_id}/feedback` |

### ai_tutor/router_admin.py (router prefix = `/tutor`, mount = `/api/v1/admin`)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | POST | `/api/v1/admin/tutor/conversations` |
| 2 | GET | `/api/v1/admin/tutor/conversations` |
| 3 | GET | `/api/v1/admin/tutor/conversations/{conversation_id}` |
| 4 | PATCH | `/api/v1/admin/tutor/conversations/{conversation_id}` |
| 5 | DELETE | `/api/v1/admin/tutor/conversations/{conversation_id}` |
| 6 | GET | `/api/v1/admin/tutor/conversations/{conversation_id}/messages` |
| 7 | POST | `/api/v1/admin/tutor/conversations/{conversation_id}/messages` |

### learning_orchestrator/router_student.py (router prefix = `/learning`, mount = `/api/v1`)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | GET | `/api/v1/learning/tasks` |
| 2 | GET | `/api/v1/learning/tasks/{task_id}` |
| 3 | GET | `/api/v1/learning/tasks/{task_id}/items` |
| 4 | POST | `/api/v1/learning/tasks/{task_id}/items/{item_id}/progress` |

### learning_orchestrator/router_admin.py (router prefix = `/learning`, mount = `/api/v1/admin`)

| # | Method | 最终路径 |
|---|--------|---------|
| 1 | POST | `/api/v1/admin/learning/tasks` |
| 2 | GET | `/api/v1/admin/learning/tasks` |
| 3 | GET | `/api/v1/admin/learning/tasks/{task_id}` |
| 4 | PATCH | `/api/v1/admin/learning/tasks/{task_id}` |
| 5 | DELETE | `/api/v1/admin/learning/tasks/{task_id}` |
| 6 | POST | `/api/v1/admin/learning/tasks/{task_id}/items` |
| 7 | PATCH | `/api/v1/admin/learning/tasks/{task_id}/items/{item_id}` |
| 8 | DELETE | `/api/v1/admin/learning/tasks/{task_id}/items/{item_id}` |
| 9 | GET | `/api/v1/admin/learning/tasks/{task_id}/progress` |
| 10 | GET | `/api/v1/admin/learning/tasks/{task_id}/progress/{student_id}` |

---

## 前端 API 调用路径（baseURL = `/api/v1`，最终路径 = baseURL + 调用路径）

### 学生端 (app)

#### app/src/api/user.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | POST | `/user/login` | `/api/v1/user/login` |
| 2 | GET | `/user/me` | `/api/v1/user/me` |
| 3 | PATCH | `/user/me` | `/api/v1/user/me` |
| 4 | POST | `/user/refresh` | `/api/v1/user/refresh` |

#### app/src/api/content.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | GET | `/content/textbooks` | `/api/v1/content/textbooks` |
| 2 | GET | `/content/textbooks/${id}` | `/api/v1/content/textbooks/{id}` |
| 3 | GET | `/content/textbooks/${textbookId}/chapters` | `/api/v1/content/textbooks/{textbookId}/chapters` |
| 4 | GET | `/content/knowledge-points` | `/api/v1/content/knowledge-points` |
| 5 | GET | `/content/knowledge-points/${id}` | `/api/v1/content/knowledge-points/{id}` |
| 6 | GET | `/content/exercises` | `/api/v1/content/exercises` |
| 7 | GET | `/content/knowledge-points/${kpId}/resources` | `/api/v1/content/knowledge-points/{kpId}/resources` |
| 8 | POST | `/content/knowledge-points/search` | `/api/v1/content/knowledge-points/search` |

#### app/src/api/learning.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | GET | `/learning/tasks` | `/api/v1/learning/tasks` |
| 2 | POST | `/learning/tasks` | `/api/v1/learning/tasks` |
| 3 | GET | `/learning/tasks/${taskId}` | `/api/v1/learning/tasks/{taskId}` |
| 4 | GET | `/learning/tasks/${taskId}/items` | `/api/v1/learning/tasks/{taskId}/items` |
| 5 | POST | `/learning/tasks/${taskId}/items/${itemId}/progress` | `/api/v1/learning/tasks/{taskId}/items/{itemId}/progress` |

#### app/src/api/tutor.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | GET | `/tutor/conversations` | `/api/v1/tutor/conversations` |
| 2 | POST | `/tutor/conversations` | `/api/v1/tutor/conversations` |
| 3 | GET | `/tutor/conversations/${id}` | `/api/v1/tutor/conversations/{id}` |
| 4 | DELETE | `/tutor/conversations/${id}` | `/api/v1/tutor/conversations/{id}` |
| 5 | POST | `/tutor/conversations/${convId}/messages` | `/api/v1/tutor/conversations/{convId}/messages` |
| 6 | GET | `/tutor/conversations/${convId}/messages` | `/api/v1/tutor/conversations/{convId}/messages` |
| 7 | POST | `/tutor/conversations/${convId}/feedback` | `/api/v1/tutor/conversations/{convId}/feedback` |

### 管理后台 (admin)

#### admin/src/api/user.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | POST | `/user/register` | `/api/v1/user/register` |
| 2 | POST | `/user/login/admin` | `/api/v1/user/login/admin` |
| 3 | POST | `/user/refresh` | `/api/v1/user/refresh` |
| 4 | GET | `/user/me` | `/api/v1/user/me` |
| 5 | PATCH | `/user/me` | `/api/v1/user/me` |
| 6 | GET | `/user/admin/users` | `/api/v1/user/admin/users` |
| 7 | GET | `/user/admin/users/${userId}` | `/api/v1/user/admin/users/{userId}` |
| 8 | PATCH | `/user/admin/users/${userId}` | `/api/v1/user/admin/users/{userId}` |

#### admin/src/api/content.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | POST | `/admin/content/textbooks` | `/api/v1/admin/content/textbooks` |
| 2 | POST | `/admin/content/textbooks/upload` | `/api/v1/admin/content/textbooks/upload` |
| 3 | GET | `/admin/content/textbooks` | `/api/v1/admin/content/textbooks` |
| 4 | GET | `/admin/content/textbooks/${id}` | `/api/v1/admin/content/textbooks/{id}` |
| 5 | PATCH | `/admin/content/textbooks/${id}` | `/api/v1/admin/content/textbooks/{id}` |
| 6 | DELETE | `/admin/content/textbooks/${id}` | `/api/v1/admin/content/textbooks/{id}` |
| 7 | POST | `/admin/content/textbooks/${textbookId}/parse` | `/api/v1/admin/content/textbooks/{textbookId}/parse` |
| 8 | GET | `/admin/content/textbooks/${textbookId}/chapters` | `/api/v1/admin/content/textbooks/{textbookId}/chapters` |
| 9 | GET | `/admin/content/knowledge-points` | `/api/v1/admin/content/knowledge-points` |
| 10 | POST | `/admin/content/knowledge-points/search` | `/api/v1/admin/content/knowledge-points/search` |
| 11 | GET | `/admin/content/exercises` | `/api/v1/admin/content/exercises` |
| 12 | POST | `/admin/content/exercises` | `/api/v1/admin/content/exercises` |
| 13 | GET | `/admin/content/exercises/${id}` | `/api/v1/admin/content/exercises/{id}` |
| 14 | PATCH | `/admin/content/exercises/${id}` | `/api/v1/admin/content/exercises/{id}` |
| 15 | DELETE | `/admin/content/exercises/${id}` | `/api/v1/admin/content/exercises/{id}` |

#### admin/src/api/learning.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | POST | `/admin/learning/tasks` | `/api/v1/admin/learning/tasks` |
| 2 | GET | `/admin/learning/tasks` | `/api/v1/admin/learning/tasks` |
| 3 | GET | `/admin/learning/tasks/${taskId}` | `/api/v1/admin/learning/tasks/{taskId}` |
| 4 | PATCH | `/admin/learning/tasks/${taskId}` | `/api/v1/admin/learning/tasks/{taskId}` |
| 5 | DELETE | `/admin/learning/tasks/${taskId}` | `/api/v1/admin/learning/tasks/{taskId}` |
| 6 | POST | `/admin/learning/tasks/${taskId}/items` | `/api/v1/admin/learning/tasks/{taskId}/items` |
| 7 | PATCH | `/admin/learning/tasks/${taskId}/items/${itemId}` | `/api/v1/admin/learning/tasks/{taskId}/items/{itemId}` |
| 8 | DELETE | `/admin/learning/tasks/${taskId}/items/${itemId}` | `/api/v1/admin/learning/tasks/{taskId}/items/{itemId}` |
| 9 | GET | `/admin/learning/tasks/${taskId}/progress` | `/api/v1/admin/learning/tasks/{taskId}/progress` |
| 10 | GET | `/admin/learning/tasks/${taskId}/progress/${studentId}` | `/api/v1/admin/learning/tasks/{taskId}/progress/{studentId}` |

#### admin/src/api/tutor.ts
| # | Method | 调用路径 | 最终路径 |
|---|--------|---------|---------|
| 1 | POST | `/admin/tutor/conversations` | `/api/v1/admin/tutor/conversations` |
| 2 | GET | `/admin/tutor/conversations` | `/api/v1/admin/tutor/conversations` |
| 3 | GET | `/admin/tutor/conversations/${convId}` | `/api/v1/admin/tutor/conversations/{convId}` |
| 4 | PATCH | `/admin/tutor/conversations/${convId}` | `/api/v1/admin/tutor/conversations/{convId}` |
| 5 | DELETE | `/admin/tutor/conversations/${convId}` | `/api/v1/admin/tutor/conversations/{convId}` |
| 6 | GET | `/admin/tutor/conversations/${convId}/messages` | `/api/v1/admin/tutor/conversations/{convId}/messages` |
| 7 | POST(SSE) | `/admin/tutor/conversations/${convId}/messages` | `/api/v1/admin/tutor/conversations/{convId}/messages` (via fetch, 非 axios)

---

## 一对一映射对比结果

### 学生端 (app) — 不匹配的接口

| # | 前端调用 | 后端路由 | 问题 |
|---|---------|---------|------|
| 1 | `GET /api/v1/content/knowledge-points/{id}` | ❌ 不存在 | 后端 `router_student.py` 没有单个知识点查询端点 |
| 2 | `GET /api/v1/content/exercises` | ❌ 不存在 | 后端 `router_student.py` 没有习题列表端点（仅 admin 有） |
| 3 | `GET /api/v1/content/knowledge-points/{kpId}/resources` | ❌ 不存在 | 后端没有该端点 |
| 4 | `POST /api/v1/learning/tasks` | ❌ 不存在 | 后端 `router_student.py` 没有创建任务端点（仅 admin 有） |

### 管理后台 (admin) — 不匹配的接口

| # | 前端调用 | 后端路由 | 问题 |
|---|---------|---------|------|
| 1 | `PATCH /api/v1/admin/content/textbooks/{id}` | 后端是 `PUT` | **HTTP 方法不匹配**：前端用 PATCH，后端定义为 PUT |
| 2 | `PATCH /api/v1/admin/content/exercises/{id}` | 后端是 `PUT` | **HTTP 方法不匹配**：前端用 PATCH，后端定义为 PUT |

### 后端有但前端没调用的接口

#### 学生端未调用：
| # | 后端路由 | 说明 |
|---|---------|------|
| 1 | `POST /api/v1/user/register` | 注册接口（学生端前端没有注册功能？）|
| 2 | `POST /api/v1/user/me/guardian` | 绑定监护人 |
| 3 | `GET /api/v1/user/me/guardian` | 查看监护人 |

#### 管理后台未调用：
| # | 后端路由 | 说明 |
|---|---------|------|
| 1 | `POST /api/v1/user/login` | 普通登录（admin 用 login/admin）|
| 2 | `POST /api/v1/user/me/guardian` | 绑定监护人（admin 不需要）|
| 3 | `GET /api/v1/user/me/guardian` | 查看监护人（admin 不需要）|
| 4 | `POST /api/v1/admin/content/knowledge-points` | 创建知识点 |
| 5 | `GET /api/v1/admin/content/knowledge-points/{kp_id}` | 查看单个知识点 |
| 6 | `PUT /api/v1/admin/content/knowledge-points/{kp_id}` | 更新知识点 |
| 7 | `DELETE /api/v1/admin/content/knowledge-points/{kp_id}` | 删除知识点 |

---

## 问题汇总与修复方案

### 🔴 严重问题（接口 404）

**1. 学生端 `GET /content/knowledge-points/{id}` — 404**
- 原因：`content_engine/router_student.py` 没有单个知识点的 GET 端点
- 修复方案 A（推荐）：在 `router_student.py` 添加 `GET /knowledge-points/{kp_id}` 端点
- 修复方案 B：前端移除该调用（如果不需要）

**2. 学生端 `GET /content/exercises` — 404**
- 原因：`content_engine/router_student.py` 没有习题列表端点，只有 admin 才有
- 修复方案 A（推荐）：在 `router_student.py` 添加 `GET /exercises` 端点（过滤 status=active）
- 修复方案 B：前端移除该调用

**3. 学生端 `GET /content/knowledge-points/{kpId}/resources` — 404**
- 原因：后端完全没有 resources 子资源端点
- 修复方案 A：在 `router_student.py` 添加 `GET /knowledge-points/{kp_id}/resources` 端点
- 修复方案 B：前端移除该调用

**4. 学生端 `POST /learning/tasks` — 404**
- 原因：`learning_orchestrator/router_student.py` 没有创建任务端点，只有 admin 才能创建
- 修复方案 A：前端移除该调用（学生不应创建任务）
- 修复方案 B：如果学生确实需要自建任务，在 `router_student.py` 添加端点

### 🟡 中等问题（HTTP 方法不匹配，返回 405）

**5. 管理后台 `PATCH /admin/content/textbooks/{id}` vs 后端 `PUT`**
- 原因：前端用 `client.patch()`，后端定义为 `@router.put()`
- 修复方案 A（推荐）：后端改为 `@router.patch()`（PATCH 更符合部分更新语义）
- 修复方案 B：前端改为 `client.put()`

**6. 管理后台 `PATCH /admin/content/exercises/{id}` vs 后端 `PUT`**
- 原因：同上
- 修复方案 A（推荐）：后端改为 `@router.patch()`
- 修复方案 B：前端改为 `client.put()`

### 🟢 低优先级（后端有但前端未调用）

这些接口后端存在但前端没有调用，属于预留功能或遗漏，不影响现有功能运行：
- 学生端注册 `POST /user/register`
- 监护人绑定 `POST/GET /user/me/guardian`
- 管理后台知识点 CRUD（create/update/delete 单个知识点）