# Admin API — 管理后台

> 父文档：[README.md](./README.md) | LLM 管理详设：[../platform/llm-management.md](../platform/llm-management.md)  
> 服务前缀：`/api/v1/admin`  
> 所有接口均需 `admin` 角色

---

## 接口总览

| 分类 | 方法 | 路径 | 说明 |
|------|------|------|------|
| **用户管理** | GET | `/admin/users` | 用户列表 |
| | GET | `/admin/users/:id` | 用户详情 |
| | PATCH | `/admin/users/:id` | 编辑用户 |
| | PATCH | `/admin/users/:id/status` | 启用/禁用 |
| **内容审核** | GET | `/admin/content/review-queue` | 待审核内容列表 |
| | GET | `/admin/content/review-queue/:id` | 审核项详情 |
| | POST | `/admin/content/review-queue/:id/approve` | 通过 |
| | POST | `/admin/content/review-queue/:id/reject` | 驳回 |
| **LLM Provider** | GET | `/admin/llm/providers` | Provider 列表 |
| | POST | `/admin/llm/providers` | 新增 Provider |
| | PATCH | `/admin/llm/providers/:id` | 更新 Provider |
| | DELETE | `/admin/llm/providers/:id` | 删除 Provider |
| **LLM 模型** | GET | `/admin/llm/models` | 模型配置列表 |
| | POST | `/admin/llm/models` | 新增模型 |
| | PATCH | `/admin/llm/models/:id` | 更新模型配置 |
| | PATCH | `/admin/llm/models/:id/status` | 变更模型状态 |
| **LLM 路由** | GET | `/admin/llm/routing-rules` | 路由规则列表 |
| | POST | `/admin/llm/routing-rules` | 新增路由规则 |
| | PATCH | `/admin/llm/routing-rules/:id` | 更新路由规则 |
| **LLM 调用日志** | GET | `/admin/llm/call-logs` | 调用日志列表 |
| | GET | `/admin/llm/call-logs/:id` | 调用日志详情 |
| **LLM 用量** | GET | `/admin/llm/usage/daily` | 每日用量统计 |
| | GET | `/admin/llm/usage/summary` | 用量汇总看板 |
| **系统配置** | GET | `/admin/sys-configs` | 配置列表 |
| | PATCH | `/admin/sys-configs/:key` | 更新配置 |
| **操作日志** | GET | `/admin/audit-logs` | 管理操作日志 |

共 **26** 个接口。

---

## 1. 用户管理

### 1.1 用户列表

```
GET /api/v1/admin/users
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role | STRING | 否 | 角色筛选：`student` / `guardian` / `teacher` / `admin` |
| status | STRING | 否 | 状态：`active` / `disabled` |
| keyword | STRING | 否 | 模糊搜索（手机号 / 昵称） |
| created_from | DATE | 否 | 注册起始日期 |
| created_to | DATE | 否 | 注册截止日期 |
| page | INT | 否 | 页码，默认 1 |
| page_size | INT | 否 | 每页条数，默认 20，最大 100 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "phone": "138****5678",
        "nickname": "小明",
        "avatar_url": "https://...",
        "role": "student",
        "status": "active",
        "last_login_at": "2026-03-25T10:00:00Z",
        "created_at": "2026-01-15T08:00:00Z"
      }
    ],
    "total": 1580,
    "page": 1,
    "page_size": 20
  }
}
```

> 注意：列表中手机号脱敏显示，详情接口返回完整手机号。

---

### 1.2 用户详情

```
GET /api/v1/admin/users/:id
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "phone": "13812345678",
    "nickname": "小明",
    "avatar_url": "https://...",
    "role": "student",
    "status": "active",
    "last_login_at": "2026-03-25T10:00:00Z",
    "created_at": "2026-01-15T08:00:00Z",
    "updated_at": "2026-03-20T12:00:00Z",
    "student_profile": {
      "grade": "grade_7",
      "school_name": "北京市第一中学",
      "textbook_versions": {
        "math": "人教版A"
      }
    },
    "guardian_bindings": [
      {
        "guardian_id": "...",
        "guardian_nickname": "小明妈妈",
        "relation": "mother",
        "verified": true,
        "bound_at": "2026-01-20T09:00:00Z"
      }
    ],
    "stats": {
      "total_study_duration_sec": 108000,
      "tasks_completed": 85,
      "avg_accuracy": 0.78,
      "last_active_at": "2026-03-25T10:00:00Z"
    }
  }
}
```

---

### 1.3 编辑用户

```
PATCH /api/v1/admin/users/:id
```

**Request Body**

```json
{
  "nickname": "小明同学",
  "role": "student"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| nickname | STRING | 否 | |
| role | STRING | 否 | 变更角色（谨慎操作） |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": "...", "nickname": "小明同学", "role": "student", "updated_at": "..." }
}
```

---

### 1.4 启用/禁用用户

```
PATCH /api/v1/admin/users/:id/status
```

**Request Body**

```json
{
  "status": "disabled",
  "reason": "违规行为"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | STRING | 是 | `active` / `disabled` |
| reason | STRING | 否 | 操作原因（记入审计日志） |

**Response 200**

```json
{
  "code": 0,
  "message": "ok"
}
```

---

## 2. 内容审核

AI 生成的内容（游戏化题目、视频脚本、练习题等）经 LLM 质量审核后，标记为需人工复审的内容进入审核队列。

### 2.1 待审核内容列表

```
GET /api/v1/admin/content/review-queue
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content_type | STRING | 否 | `game` / `video_script` / `practice` |
| review_status | STRING | 否 | `pending` / `approved` / `rejected`，默认 `pending` |
| knowledge_point_id | UUID | 否 | 按知识点筛选 |
| page | INT | 否 | 页码，默认 1 |
| page_size | INT | 否 | 每页条数，默认 20，最大 100 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "content_type": "game",
        "title": "勾股定理 — 拖拽匹配",
        "knowledge_point_name": "勾股定理",
        "ai_quality_score": 0.75,
        "ai_review_comment": "题目表述略有歧义，建议人工确认",
        "review_status": "pending",
        "created_at": "2026-03-24T14:00:00Z"
      }
    ],
    "total": 23,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 2.2 审核项详情

```
GET /api/v1/admin/content/review-queue/:id
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "content_type": "game",
    "title": "勾股定理 — 拖拽匹配",
    "knowledge_point_id": "...",
    "knowledge_point_name": "勾股定理",
    "content_data": {
      "game_type": "drag_match",
      "difficulty": "intermediate",
      "items": [
        { "left": "3² + 4²", "right": "5²" },
        { "left": "5² + 12²", "right": "13²" }
      ],
      "explanation": "勾股定理：a² + b² = c²，其中 c 为斜边"
    },
    "ai_quality_score": 0.75,
    "ai_review_comment": "题目表述略有歧义，建议人工确认",
    "review_status": "pending",
    "reviewed_by": null,
    "reviewed_at": null,
    "created_at": "2026-03-24T14:00:00Z",
    "generation_trace_id": "a1b2c3d4-..."
  }
}
```

> `generation_trace_id` 可关联到 LLM 调用日志，追溯生成过程。

---

### 2.3 通过审核

```
POST /api/v1/admin/content/review-queue/:id/approve
```

**Request Body**

```json
{
  "comment": "内容准确，可发布"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| comment | STRING | 否 | 审核备注 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "review_status": "approved",
    "reviewed_by": "...",
    "reviewed_at": "2026-03-25T16:00:00Z"
  }
}
```

---

### 2.4 驳回

```
POST /api/v1/admin/content/review-queue/:id/reject
```

**Request Body**

```json
{
  "reason": "答案选项有误，C 选项应为 25 而非 26",
  "action": "regenerate"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| reason | STRING | 是 | 驳回原因 |
| action | STRING | 否 | 后续动作：`regenerate`（重新生成）/ `archive`（归档弃用），默认 `archive` |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "review_status": "rejected",
    "reviewed_by": "...",
    "reviewed_at": "2026-03-25T16:00:00Z",
    "regeneration_task_id": "..."
  }
}
```

> `action = "regenerate"` 时返回 `regeneration_task_id`，可用于跟踪重新生成进度。

---

## 3. LLM Provider 管理

> 完整数据模型和路由决策逻辑见 [../platform/llm-management.md](../platform/llm-management.md)

### 3.1 Provider 列表

```
GET /api/v1/admin/llm/providers
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "provider_name": "deepseek",
        "display_name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "status": "active",
        "model_count": 2,
        "created_at": "2026-01-01T00:00:00Z"
      }
    ]
  }
}
```

> `api_key_encrypted` 不在列表接口中返回，仅展示是否已配置（`has_api_key: true`）。

---

### 3.2 新增 Provider

```
POST /api/v1/admin/llm/providers
```

**Request Body**

```json
{
  "provider_name": "deepseek",
  "display_name": "DeepSeek",
  "base_url": "https://api.deepseek.com/v1",
  "api_key": "sk-xxxxxxxx",
  "config": {
    "timeout_sec": 60,
    "max_retries": 2
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider_name | STRING | 是 | 唯一标识，如 `deepseek`, `openai` |
| display_name | STRING | 是 | 展示名 |
| base_url | STRING | 是 | API 基础地址 |
| api_key | STRING | 是 | API 密钥（服务端 AES 加密存储） |
| config | OBJECT | 否 | 额外配置（超时、重试等） |

**Response 201**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "provider_name": "deepseek",
    "display_name": "DeepSeek",
    "status": "active",
    "created_at": "..."
  }
}
```

---

### 3.3 更新 Provider

```
PATCH /api/v1/admin/llm/providers/:id
```

**Request Body** — 所有字段均可选

```json
{
  "display_name": "DeepSeek V3",
  "base_url": "https://api.deepseek.com/v2",
  "api_key": "sk-newkey",
  "config": { "timeout_sec": 90 }
}
```

**Response 200** — 返回更新后的 Provider 对象。

---

### 3.4 删除 Provider（软删除）

```
DELETE /api/v1/admin/llm/providers/:id
```

删除前校验：若该 Provider 下仍有 `active` 状态的模型配置，返回 `42003` 错误。

**Response 200**

```json
{
  "code": 0,
  "message": "ok"
}
```

**Response 409**

```json
{
  "code": 42003,
  "message": "该 Provider 下仍有活跃模型，请先禁用或迁移"
}
```

---

## 4. LLM 模型配置

### 4.1 模型配置列表

```
GET /api/v1/admin/llm/models
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| provider_id | UUID | 否 | 按 Provider 筛选 |
| model_type | STRING | 否 | `chat` / `embedding` |
| status | STRING | 否 | `active` / `disabled` / `deprecated` |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "provider_id": "...",
        "provider_name": "deepseek",
        "model_name": "deepseek-v3",
        "display_name": "DeepSeek V3",
        "model_type": "chat",
        "status": "active",
        "max_tokens": 8192,
        "default_temperature": 0.70,
        "input_price_per_1k": 0.001000,
        "output_price_per_1k": 0.002000,
        "rate_limit_rpm": 60,
        "rate_limit_tpm": 100000
      }
    ]
  }
}
```

---

### 4.2 新增模型

```
POST /api/v1/admin/llm/models
```

**Request Body**

```json
{
  "provider_id": "...",
  "model_name": "deepseek-v3",
  "display_name": "DeepSeek V3",
  "model_type": "chat",
  "max_tokens": 8192,
  "default_temperature": 0.70,
  "input_price_per_1k": 0.001000,
  "output_price_per_1k": 0.002000,
  "max_cost_per_call": 0.5000,
  "rate_limit_rpm": 60,
  "rate_limit_tpm": 100000,
  "config": {}
}
```

唯一约束 `(provider_id, model_name)`，重复返回 `42004`。

**Response 201**

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": "...", "model_name": "deepseek-v3", "status": "active", "created_at": "..." }
}
```

---

### 4.3 更新模型配置

```
PATCH /api/v1/admin/llm/models/:id
```

可更新字段：`display_name`, `max_tokens`, `default_temperature`, 价格相关字段, `rate_limit_*`, `max_cost_per_call`, `config`。

`model_name` 和 `provider_id` 创建后不可变更。

---

### 4.4 变更模型状态

```
PATCH /api/v1/admin/llm/models/:id/status
```

**Request Body**

```json
{
  "status": "deprecated",
  "reason": "官方已下线该模型版本"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | STRING | 是 | `active` / `disabled` / `deprecated` |
| reason | STRING | 否 | 操作原因（记入审计日志） |

状态变更约束：
- `deprecated` → 不可变回 `active`，只能新建
- 设为 `disabled` / `deprecated` 时，自动检查关联的路由规则是否有备选

---

## 5. LLM 路由规则

### 5.1 路由规则列表

```
GET /api/v1/admin/llm/routing-rules
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | STRING | 否 | 按任务类型筛选 |
| is_active | BOOLEAN | 否 | 是否启用 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "task_type": "game_generate",
        "primary_model": {
          "id": "...",
          "model_name": "deepseek-v3",
          "provider_name": "deepseek"
        },
        "fallback_model": {
          "id": "...",
          "model_name": "qwen-2.5-72b",
          "provider_name": "qwen"
        },
        "priority": 1,
        "is_active": true,
        "conditions": { "grade_range": "grade_7-grade_9" }
      }
    ]
  }
}
```

---

### 5.2 新增路由规则

```
POST /api/v1/admin/llm/routing-rules
```

**Request Body**

```json
{
  "task_type": "game_generate",
  "primary_model_id": "...",
  "fallback_model_id": "...",
  "priority": 1,
  "is_active": true,
  "conditions": { "grade_range": "grade_7-grade_9" }
}
```

---

### 5.3 更新路由规则

```
PATCH /api/v1/admin/llm/routing-rules/:id
```

可更新字段：`primary_model_id`, `fallback_model_id`, `priority`, `is_active`, `conditions`。

`task_type` 创建后不可变更。

---

## 6. LLM 调用日志

### 6.1 调用日志列表

```
GET /api/v1/admin/llm/call-logs
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | STRING | 否 | 任务类型 |
| model_name | STRING | 否 | 模型名 |
| status | STRING | 否 | `success` / `failed` / `timeout` / `fallback` |
| trace_id | STRING | 否 | 链路追踪 ID（精确匹配） |
| caller_service | STRING | 否 | 调用方服务名 |
| start_time | DATETIME | 否 | 起始时间 |
| end_time | DATETIME | 否 | 结束时间 |
| min_duration_ms | INT | 否 | 最小耗时（筛选慢调用） |
| page | INT | 否 | 默认 1 |
| page_size | INT | 否 | 默认 20，最大 100 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "trace_id": "a1b2c3d4-...",
        "task_type": "game_generate",
        "provider_name": "deepseek",
        "model_name": "deepseek-v3",
        "status": "success",
        "input_tokens": 1200,
        "output_tokens": 800,
        "duration_ms": 2300,
        "estimated_cost_yuan": 0.0028,
        "caller_service": "content-engine",
        "user_id": "...",
        "created_at": "2026-03-25T14:30:00Z"
      }
    ],
    "total": 4500,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 6.2 调用日志详情

```
GET /api/v1/admin/llm/call-logs/:id
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "trace_id": "a1b2c3d4-...",
    "span_id": "1234abcd",
    "parent_span_id": "5678efgh",
    "task_type": "game_generate",
    "provider_name": "deepseek",
    "model_name": "deepseek-v3",
    "status": "success",
    "input_tokens": 1200,
    "output_tokens": 800,
    "total_tokens": 2000,
    "duration_ms": 2300,
    "estimated_cost_yuan": 0.0028,
    "input_messages": "[已脱敏] system: ..., user: 生成勾股定理相关的...",
    "output_content": "{ \"game_type\": \"drag_match\", ... }",
    "model_params": {
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "caller_service": "content-engine",
    "user_id": "...",
    "error_message": null,
    "created_at": "2026-03-25T14:30:00Z"
  }
}
```

> `input_messages` 已脱敏存储（包含学生个人信息的内容被替换）。

---

## 7. LLM 用量统计

### 7.1 每日用量

```
GET /api/v1/admin/llm/usage/daily
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | DATE | 是 | 起始日期 |
| end_date | DATE | 是 | 结束日期，最大 90 天 |
| provider_name | STRING | 否 | 按 Provider 筛选 |
| model_name | STRING | 否 | 按模型筛选 |
| task_type | STRING | 否 | 按任务类型筛选 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "stat_date": "2026-03-25",
        "provider_name": "deepseek",
        "model_name": "deepseek-v3",
        "task_type": "game_generate",
        "total_calls": 250,
        "success_calls": 245,
        "failed_calls": 5,
        "total_input_tokens": 300000,
        "total_output_tokens": 200000,
        "total_cost_yuan": 0.70,
        "avg_duration_ms": 2100,
        "p95_duration_ms": 4500
      }
    ],
    "total": 48,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 7.2 用量汇总看板

```
GET /api/v1/admin/llm/usage/summary
```

管理后台 LLM 看板首屏数据。

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | STRING | 否 | `today` / `week` / `month`，默认 `today` |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "period": "today",
    "total_calls": 4500,
    "success_rate": 0.987,
    "total_cost_yuan": 128.50,
    "total_tokens": 9000000,
    "avg_duration_ms": 2300,
    "by_provider": [
      {
        "provider_name": "deepseek",
        "calls": 3800,
        "cost_yuan": 45.60,
        "avg_duration_ms": 2100
      },
      {
        "provider_name": "qwen",
        "calls": 700,
        "cost_yuan": 82.90,
        "avg_duration_ms": 3200
      }
    ],
    "by_task_type": [
      {
        "task_type": "game_generate",
        "calls": 1200,
        "cost_yuan": 28.50
      },
      {
        "task_type": "practice_generate",
        "calls": 1000,
        "cost_yuan": 24.00
      }
    ],
    "alerts": [
      {
        "type": "cost_warning",
        "message": "今日费用已达月预算的 15%",
        "severity": "warning"
      }
    ]
  }
}
```

---

## 8. 系统配置

管理系统级配置参数（存储于 `sys_configs` 表），如 LLM 月预算、功能开关等。

### 8.1 配置列表

```
GET /api/v1/admin/sys-configs
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| config_group | STRING | 否 | 按分组筛选：`general` / `sms` / `llm` / `security` / `feature_flag` |
| is_active | BOOLEAN | 否 | 按启用状态筛选 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "uuid",
        "config_key": "llm.default_model",
        "config_value": "deepseek-v3",
        "value_type": "string",
        "config_group": "llm",
        "description": "默认 LLM 模型",
        "is_sensitive": false,
        "is_active": true,
        "updated_at": "2026-03-25T10:00:00Z"
      }
    ],
    "total": 15
  }
}
```

> `is_sensitive = true` 的配置项，`config_value` 返回 `"***"` 脱敏值。

---

### 8.2 更新配置

```
PUT /api/v1/admin/sys-configs/:config_key
```

**Request Body**

```json
{
  "config_value": "gpt-4o",
  "change_reason": "切换默认模型"
}
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "config_key": "llm.default_model",
    "config_value": "gpt-4o",
    "value_type": "string",
    "config_group": "llm",
    "is_active": true,
    "updated_at": "2026-03-25T15:30:00Z"
  }
}
```

> 每次更新自动写入 `sys_config_history`，并失效 Redis 缓存。

---

### 8.3 配置变更历史

```
GET /api/v1/admin/sys-configs/:config_key/history
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | INT | 否 | 页码，默认 1 |
| page_size | INT | 否 | 每页条数，默认 20 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "uuid",
        "config_key": "llm.default_model",
        "old_value": "deepseek-v3",
        "new_value": "gpt-4o",
        "change_reason": "切换默认模型",
        "operator_id": "uuid",
        "created_at": "2026-03-25T15:30:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 9. 审计日志

查询管理员操作的审计日志（append-only，不可修改/删除）。

### 9.1 审计日志列表

```
GET /api/v1/admin/audit-logs
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | STRING | 否 | 操作类型：`create` / `update` / `delete` / `login` / `export` / `config_change` / `role_change` |
| resource_type | STRING | 否 | 资源类型：`user` / `textbook` / `task` / `sys_config` / `model_config` |
| operator_id | UUID | 否 | 操作人 ID |
| start_time | DATETIME | 否 | 起始时间 |
| end_time | DATETIME | 否 | 结束时间 |
| page | INT | 否 | 页码，默认 1 |
| page_size | INT | 否 | 每页条数，默认 20，最大 100 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "uuid",
        "action": "config_change",
        "resource_type": "sys_config",
        "resource_id": "uuid",
        "operator_id": "uuid",
        "operator_role": "admin",
        "operator_ip": "192.168.1.100",
        "request_method": "PUT",
        "request_path": "/api/v1/admin/sys-configs/llm.default_model",
        "changes": {
          "before": { "config_value": "deepseek-v3" },
          "after": { "config_value": "gpt-4o" }
        },
        "trace_id": "abc123def456",
        "created_at": "2026-03-25T15:30:00Z"
      }
    ],
    "total": 320,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 9.2 审计日志详情

```
GET /api/v1/admin/audit-logs/:id
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "uuid",
    "action": "role_change",
    "resource_type": "user",
    "resource_id": "uuid",
    "operator_id": "uuid",
    "operator_role": "admin",
    "operator_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0 ...",
    "request_method": "PUT",
    "request_path": "/api/v1/admin/users/uuid/role",
    "changes": {
      "before": { "role": "student" },
      "after": { "role": "teacher" }
    },
    "metadata": {
      "reason": "教师认证通过"
    },
    "trace_id": "abc123def456",
    "created_at": "2026-03-25T15:30:00Z"
  }
}
```

---

### 9.3 审计日志导出

```
POST /api/v1/admin/audit-logs/export
```

**Request Body**

```json
{
  "start_time": "2026-03-01T00:00:00Z",
  "end_time": "2026-03-25T23:59:59Z",
  "action": "role_change",
  "format": "csv"
}
```

**Response 202**

```json
{
  "code": 0,
  "message": "导出任务已创建",
  "data": {
    "task_id": "uuid",
    "status": "processing",
    "estimated_seconds": 30
  }
}
```

> 导出为异步任务，完成后通过通知下发下载链接（MinIO 签名 URL，1h 有效）。

---

## 枚举定义汇总

| 枚举名 | 值 | 使用位置 |
|--------|-----|----------|
| user_role | `student` / `guardian` / `admin` / `teacher` | 用户管理 |
| user_status | `active` / `disabled` / `deleted` | 用户管理 |
| review_status | `pending` / `approved` / `rejected` | 内容审核 |
| review_content_type | `game` / `practice` / `exercise` / `video_script` | 内容审核 |
| provider_status | `active` / `disabled` | LLM Provider |
| model_status | `active` / `disabled` / `deprecated` | LLM 模型 |
| routing_strategy | `priority` / `round_robin` / `cost_optimized` / `latency_optimized` | LLM 路由 |
| call_status | `success` / `failed` / `timeout` | LLM 调用日志 |
| config_group | `general` / `sms` / `llm` / `security` / `feature_flag` / `notification` / `media` | 系统配置 |
| value_type | `string` / `number` / `boolean` / `json` | 系统配置 |
| audit_action | `create` / `update` / `delete` / `login` / `logout` / `export` / `config_change` / `role_change` | 审计日志 |
| audit_resource_type | `user` / `textbook` / `knowledge_point` / `resource` / `task` / `sys_config` / `model_config` / `notification_template` | 审计日志 |