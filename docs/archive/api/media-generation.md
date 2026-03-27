# Media Generation API — 内容生成

> 父文档：[README.md](./README.md) | 数据模型：[data-model.md](../data-model.md) media-generation schema  
> 服务前缀：`/api/v1`

---

## 接口总览

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| POST | `/resources/generate` | 🛡️ admin/teacher | 触发内容生成 |
| GET | `/resources/generate/:taskId` | 🛡️ admin/teacher | 查询生成进度 |
| GET | `/resources` | 👤 all | 生成资源列表 |
| GET | `/resources/:id` | 👤 all | 资源详情 |
| PATCH | `/resources/:id` | 🛡️ admin | 更新资源 |
| DELETE | `/resources/:id` | 🛡️ admin | 删除资源 |
| POST | `/resources/:id/review` | 🛡️ admin | 人工审核 |
| POST | `/resources/:id/regenerate` | 🛡️ admin | 重新生成 |
| GET | `/prompt-templates` | 🛡️ admin | Prompt 模板列表 |
| GET | `/prompt-templates/:id` | 🛡️ admin | 模板详情 |
| POST | `/prompt-templates` | 🛡️ admin | 创建模板 |
| PATCH | `/prompt-templates/:id` | 🛡️ admin | 更新模板 |
| POST | `/resources/batch-generate` | 🛡️ admin | 批量生成 |

---

## 1. 内容生成

### 1.1 触发生成

```
POST /api/v1/resources/generate
```

根据知识点 + 资源类型 + Prompt 模板，调用 LLM 异步生成内容。

**Request Body**

```json
{
  "knowledge_point_id": "kp-uuid",
  "resource_type": "game_quiz",
  "difficulty": "basic",
  "prompt_template_id": "math.basic.game_quiz.v1",
  "params": {
    "level_count": 5,
    "time_limit_sec": 300,
    "language": "zh-CN"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| knowledge_point_id | uuid | ✅ | 目标知识点 |
| resource_type | string | ✅ | `game_quiz` / `game_drag_match` / `video_script` / `practice_set` |
| difficulty | string | | `basic`（默认）/ `intermediate` / `advanced` |
| prompt_template_id | string | | 指定模板，不传则自动匹配 |
| params | object | | 生成参数，覆盖模板默认值 |

**Response** `202 Accepted`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "gen-task-uuid",
    "status": "pending",
    "resource_type": "game_quiz",
    "estimated_duration_s": 30
  }
}
```

### 1.2 查询生成进度

```
GET /api/v1/resources/generate/:taskId
```

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "gen-task-uuid",
    "status": "completed",
    "resource_id": "resource-uuid",
    "resource_type": "game_quiz",
    "quality_score": 0.85,
    "llm_model": "deepseek-v3",
    "generation_cost_ms": 4520,
    "started_at": "...",
    "completed_at": "..."
  }
}
```

> `status` 枚举：`pending` / `processing` / `completed` / `failed`

### 1.3 批量生成

```
POST /api/v1/resources/batch-generate
```

对多个知识点批量触发生成，排入队列逐个处理。

**Request Body**

```json
{
  "items": [
    { "knowledge_point_id": "kp-uuid-1", "resource_type": "game_quiz" },
    { "knowledge_point_id": "kp-uuid-1", "resource_type": "practice_set" },
    { "knowledge_point_id": "kp-uuid-2", "resource_type": "video_script" }
  ],
  "difficulty": "basic",
  "prompt_template_id": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| items | array | ✅ | 生成任务列表，最多 20 条 |
| difficulty | string | | 统一难度，可被 item 级覆盖 |

**Response** `202`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "batch_id": "batch-uuid",
    "total": 3,
    "tasks": [
      { "task_id": "task-1", "knowledge_point_id": "kp-uuid-1", "resource_type": "game_quiz", "status": "pending" },
      { "task_id": "task-2", "knowledge_point_id": "kp-uuid-1", "resource_type": "practice_set", "status": "pending" },
      { "task_id": "task-3", "knowledge_point_id": "kp-uuid-2", "resource_type": "video_script", "status": "pending" }
    ]
  }
}
```

---

## 2. 资源管理

### 2.1 资源列表

```
GET /api/v1/resources
```

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| knowledge_point_id | uuid | 按知识点筛选 |
| resource_type | string | 按资源类型筛选 |
| difficulty | string | 按难度筛选 |
| review_status | string | `auto` / `approved` / `rejected` |
| quality_score_min | float | 最低质量分（0-1） |
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
        "id": "resource-uuid",
        "knowledge_point_id": "kp-uuid",
        "knowledge_point_name": "正数和负数的概念",
        "resource_type": "game_quiz",
        "title": "有理数选择闯关",
        "difficulty": "basic",
        "version": 1,
        "quality_score": 0.85,
        "review_status": "auto",
        "llm_model": "deepseek-v3",
        "created_at": "..."
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20
  }
}
```

### 2.2 资源详情

```
GET /api/v1/resources/:id
```

返回完整资源信息，含 `content` JSONB 原始数据。

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "resource-uuid",
    "knowledge_point_id": "kp-uuid",
    "resource_type": "game_quiz",
    "title": "有理数选择闯关",
    "content": {
      "levels": [
        {
          "level_no": 1,
          "question": "一元二次方程的一般形式是？",
          "options": ["ax²+bx+c=0", "ax+b=0", "ax³+bx=0", "a/x+b=0"],
          "correct_index": 0,
          "explanation": "标准形式为 ax²+bx+c=0 (a≠0)",
          "difficulty": "basic"
        }
      ],
      "total_levels": 5,
      "time_limit_sec": 300
    },
    "difficulty": "basic",
    "version": 1,
    "quality_score": 0.85,
    "review_status": "auto",
    "prompt_template_id": "math.basic.game_quiz.v1",
    "llm_model": "deepseek-v3",
    "generation_cost_ms": 4520,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### 2.3 更新资源

```
PATCH /api/v1/resources/:id
```

人工修正生成内容（`title`、`content`、`difficulty`），自动 `version++`。

**Request Body**

```json
{
  "title": "有理数选择闯关（修订）",
  "content": { "...": "修改后的完整 JSONB" }
}
```

### 2.4 删除资源

```
DELETE /api/v1/resources/:id
```

软删除。已在学习任务中使用的资源不可删除（`42002`）。

---

## 3. 审核与重新生成

### 3.1 人工审核

```
POST /api/v1/resources/:id/review
```

**Request Body**

```json
{
  "action": "approved",
  "comment": "内容准确，难度适当"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | ✅ | `approved` / `rejected` |
| comment | string | | 审核意见 |

**Response** `200`

### 3.2 重新生成

```
POST /api/v1/resources/:id/regenerate
```

基于同一知识点和模板重新生成，旧版本保留（version 递增）。

**Request Body**

```json
{
  "prompt_template_id": "math.basic.game_quiz.v2",
  "params": { "level_count": 8 }
}
```

**Response** `202` — 同 1.1 触发生成。

---

## 4. Prompt 模板管理

### 4.1 模板列表

```
GET /api/v1/prompt-templates
```

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| resource_type | string | 按资源类型筛选 |
| subject | string | 按学科筛选 |
| is_active | bool | 是否启用 |
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
        "id": "math.basic.game_quiz.v1",
        "resource_type": "game_quiz",
        "subject": "math",
        "grade_range": "grade_7-grade_9",
        "is_active": true,
        "version": 1,
        "variables": [
          { "name": "knowledge_point", "type": "string", "required": true },
          { "name": "level_count", "type": "int", "default": 5 },
          { "name": "time_limit_sec", "type": "int", "default": 300 }
        ],
        "created_at": "..."
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.2 模板详情

```
GET /api/v1/prompt-templates/:id
```

返回完整模板信息，含 `template_content`（Jinja2 源码）。

### 4.3 创建模板

```
POST /api/v1/prompt-templates
```

**Request Body**

```json
{
  "id": "math.basic.game_quiz.v2",
  "resource_type": "game_quiz",
  "subject": "math",
  "grade_range": "grade_7-grade_9",
  "template_content": "你是一个教育内容生成专家...\n\n知识点：{{ knowledge_point }}\n难度：{{ difficulty }}\n关卡数量：{{ level_count }}\n...",
  "variables": [
    { "name": "knowledge_point", "type": "string", "required": true },
    { "name": "difficulty", "type": "string", "default": "basic" },
    { "name": "level_count", "type": "int", "default": 5 }
  ]
}
```

**Response** `201`

### 4.4 更新模板

```
PATCH /api/v1/prompt-templates/:id
```

更新模板内容/变量，自动 `version++`。已被使用的模板建议创建新版本而非直接修改。

---

## 5. 错误码

| 错误码 | 说明 |
|--------|------|
| 42001 | 资源不存在 |
| 42002 | 资源已被学习任务引用，不可删除 |
| 42003 | 生成任务不存在 |
| 42004 | 生成任务正在进行中，不可重复触发 |
| 42005 | 不支持的资源类型 |
| 42010 | 模板不存在 |
| 42011 | 模板 ID 已存在 |
| 42012 | 模板变量校验失败 |
| 42020 | 批量生成数量超限（最多 20） |
| 42021 | 关联知识点不存在 |
