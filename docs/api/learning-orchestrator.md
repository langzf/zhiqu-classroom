# Learning Orchestrator API — 学习编排

> 父文档：[README.md](./README.md) | 数据模型：[data-model.md](../data-model.md) learning-orchestrator schema  
> 服务前缀：`/api/v1`

---

## 接口总览

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| POST | `/tasks` | 🛡️ teacher/admin | 创建任务 |
| GET | `/tasks` | 🛡️ teacher/admin | 任务列表（教师视角） |
| GET | `/tasks/:id` | 👤 all | 任务详情 |
| PATCH | `/tasks/:id` | 🛡️ teacher/admin | 更新任务 |
| DELETE | `/tasks/:id` | 🛡️ teacher/admin | 删除任务 |
| POST | `/tasks/:id/publish` | 🛡️ teacher/admin | 发布任务 |
| POST | `/tasks/:id/archive` | 🛡️ teacher/admin | 归档任务 |
| POST | `/tasks/:id/assign` | 🛡️ teacher/admin | 分配任务 |
| GET | `/tasks/:id/assignments` | 🛡️ teacher/admin | 任务分配列表 |
| DELETE | `/tasks/:id/assignments/:assignmentId` | 🛡️ teacher/admin | 取消分配 |
| GET | `/my/tasks` | 👤 student | 学生 — 我的任务列表 |
| GET | `/my/tasks/:taskId` | 👤 student | 学生 — 任务详情 + 进度 |
| POST | `/my/tasks/:taskId/records` | 👤 student | 学生 — 提交学习记录 |
| GET | `/my/tasks/:taskId/records` | 👤 student | 学生 — 学习记录列表 |
| GET | `/tasks/:id/progress` | 🛡️ teacher/admin | 教师 — 任务完成进度 |
| GET | `/tasks/:id/progress/:studentId` | 🛡️ teacher/admin | 教师 — 单个学生进度详情 |

---

## 1. 任务管理（教师/管理员）

### 1.1 创建任务

```
POST /api/v1/tasks
```

**Request Body**

```json
{
  "title": "第一章课后练习 - 有理数",
  "description": "完成有理数相关的游戏闯关和练习题",
  "textbook_id": "textbook-uuid",
  "chapter_id": "chapter-uuid",
  "target_knowledge_points": ["kp-uuid-1", "kp-uuid-2"],
  "resource_refs": [
    { "resource_id": "res-uuid-1", "resource_type": "game_quiz", "required": true },
    { "resource_id": "res-uuid-2", "resource_type": "practice_set", "required": true },
    { "resource_id": "res-uuid-3", "resource_type": "video_script", "required": false }
  ],
  "task_type": "after_class",
  "difficulty": "basic",
  "estimated_duration_min": 30
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 任务标题，最长 200 字 |
| description | string | | 任务说明 |
| textbook_id | uuid | ✅ | 关联教材 |
| chapter_id | uuid | | 关联章节 |
| target_knowledge_points | uuid[] | ✅ | 目标知识点（至少 1 个） |
| resource_refs | array | ✅ | 关联资源列表（至少 1 个） |
| resource_refs[].resource_id | uuid | ✅ | 资源 ID |
| resource_refs[].resource_type | string | ✅ | `game_quiz` / `practice_set` / `video_script` / `game_drag_match` |
| resource_refs[].required | bool | | 是否必做，默认 true |
| task_type | string | | `after_class`（默认）/ `review` / `assessment` |
| difficulty | string | | `basic`（默认）/ `intermediate` / `advanced` |
| estimated_duration_min | int | | 预估完成时长（分钟） |

**Response** `201`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "task-uuid",
    "title": "第一章课后练习 - 有理数",
    "task_type": "after_class",
    "status": "draft",
    "resource_count": 3,
    "created_at": "2026-03-25T16:00:00+08:00"
  }
}
```

### 1.2 任务列表

```
GET /api/v1/tasks
```

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| textbook_id | uuid | 按教材筛选 |
| chapter_id | uuid | 按章节筛选 |
| task_type | string | 按任务类型筛选 |
| status | string | `draft` / `published` / `archived` |
| keyword | string | 模糊搜索标题 |
| page | int | 页码，默认 1 |
| page_size | int | 每页条数，默认 20 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "task-uuid",
        "title": "第一章课后练习 - 有理数",
        "task_type": "after_class",
        "difficulty": "basic",
        "status": "published",
        "resource_count": 3,
        "assignment_count": 35,
        "completion_rate": 0.72,
        "published_at": "...",
        "created_at": "..."
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20
  }
}
```

### 1.3 任务详情

```
GET /api/v1/tasks/:id
```

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "task-uuid",
    "title": "第一章课后练习 - 有理数",
    "description": "完成有理数相关的游戏闯关和练习题",
    "textbook_id": "textbook-uuid",
    "textbook_title": "人教版数学七年级上册",
    "chapter_id": "chapter-uuid",
    "chapter_title": "第一章 有理数",
    "target_knowledge_points": [
      { "id": "kp-uuid-1", "name": "正数和负数的概念" },
      { "id": "kp-uuid-2", "name": "有理数的分类" }
    ],
    "resource_refs": [
      { "resource_id": "res-uuid-1", "resource_type": "game_quiz", "title": "有理数选择闯关", "required": true },
      { "resource_id": "res-uuid-2", "resource_type": "practice_set", "title": "有理数练习", "required": true },
      { "resource_id": "res-uuid-3", "resource_type": "video_script", "title": "有理数讲解", "required": false }
    ],
    "task_type": "after_class",
    "difficulty": "basic",
    "estimated_duration_min": 30,
    "status": "published",
    "assignment_count": 35,
    "completion_rate": 0.72,
    "published_at": "...",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### 1.4 更新任务

```
PATCH /api/v1/tasks/:id
```

仅 `draft` 状态可修改核心字段（`resource_refs`、`target_knowledge_points`）。已发布任务只可修改 `title`、`description`、`estimated_duration_min`。

**Request Body** — 仅传需要更新的字段。

### 1.5 删除任务

```
DELETE /api/v1/tasks/:id
```

软删除。已发布且有学习记录的任务不可删除（`43002`）。

**Response** `200`

```json
{ "code": 0, "message": "ok", "data": null }
```

### 1.6 发布任务

```
POST /api/v1/tasks/:id/publish
```

将任务从 `draft` → `published`。要求至少有 1 个 required 资源。

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": "task-uuid", "status": "published", "published_at": "..." }
}
```

### 1.7 归档任务

```
POST /api/v1/tasks/:id/archive
```

将任务从 `published` → `archived`。归档后学生不可再提交新记录，但历史记录保留。

**Response** `200`

---

## 2. 任务分配

### 2.1 分配任务

```
POST /api/v1/tasks/:id/assign
```

支持三种分配方式：个人、班级、年级。

**Request Body**

```json
{
  "assign_type": "class",
  "target_ids": ["class-uuid-1", "class-uuid-2"],
  "deadline": "2026-04-01T23:59:59+08:00",
  "notify": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| assign_type | string | ✅ | `individual` / `class` / `grade` |
| target_ids | uuid[] | ✅ | 学生 ID / 班级 ID / 年级 ID |
| deadline | datetime | | 截止时间 |
| notify | bool | | 是否推送通知，默认 true |

> 按班级/年级分配时，系统自动展开为 individual 级记录（一个学生一条 `task_assignments`）。

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "assigned_count": 35,
    "skipped_count": 0,
    "skipped_reason": null
  }
}
```

### 2.2 任务分配列表

```
GET /api/v1/tasks/:id/assignments
```

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | `pending` / `in_progress` / `completed` / `expired` |
| class_id | uuid | 按班级筛选 |
| page | int | 页码 |
| page_size | int | 每页条数 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "assignment-uuid",
        "student_id": "student-uuid",
        "student_name": "张小明",
        "class_name": "七年级3班",
        "assign_type": "class",
        "status": "completed",
        "progress_pct": 100,
        "score": 85,
        "deadline": "2026-04-01T23:59:59+08:00",
        "started_at": "...",
        "completed_at": "..."
      }
    ],
    "total": 35,
    "page": 1,
    "page_size": 20,
    "summary": {
      "total": 35,
      "pending": 5,
      "in_progress": 8,
      "completed": 20,
      "expired": 2,
      "completion_rate": 0.57,
      "avg_score": 78.5
    }
  }
}
```

### 2.3 取消分配

```
DELETE /api/v1/tasks/:id/assignments/:assignmentId
```

仅 `pending` 状态的分配可取消。已开始学习的分配不可取消（`43011`）。
```
