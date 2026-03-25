# 1. 对话管理

> 父文档：[README.md](./README.md)

---

## 1.1 创建对话

```
POST /api/v1/conversations
```

创建一个新的 AI 辅导对话会话。每个对话绑定到一个学习场景（知识点/任务/自由提问）。

**Request Body**

```json
{
  "title": "有理数加减法不太懂",
  "context_type": "knowledge_point",
  "context_id": "kp-uuid-1",
  "task_id": "task-uuid",
  "initial_message": "老师，有理数的加法法则是什么？"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | | 对话标题，不填则自动生成 |
| context_type | string | ✅ | `knowledge_point` / `task` / `free` |
| context_id | uuid | 条件 | `knowledge_point` / `task` 时必填 |
| task_id | uuid | | 关联的任务 ID（辅助上下文） |
| initial_message | string | | 首条消息，填写后自动触发 AI 回复 |

> **context_type 说明：**
> - `knowledge_point`：针对特定知识点的辅导，AI 会围绕该知识点回答
> - `task`：在做某个任务时遇到问题，AI 会参考任务内容和关联知识点
> - `free`：自由提问，AI 根据学生年级/教材范围回答

**Response** `201`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "conv-uuid",
    "title": "有理数加减法不太懂",
    "context_type": "knowledge_point",
    "context_id": "kp-uuid-1",
    "context_name": "有理数的加法",
    "task_id": "task-uuid",
    "status": "active",
    "message_count": 2,
    "messages": [
      {
        "id": "msg-uuid-1",
        "role": "user",
        "content": "老师，有理数的加法法则是什么？",
        "created_at": "2026-03-25T19:00:00+08:00"
      },
      {
        "id": "msg-uuid-2",
        "role": "assistant",
        "content": "好问题！有理数的加法法则分三种情况...",
        "thinking_steps": ["理解学生问题", "检索知识点", "组织回答"],
        "knowledge_refs": ["kp-uuid-1"],
        "created_at": "2026-03-25T19:00:02+08:00"
      }
    ],
    "created_at": "2026-03-25T19:00:00+08:00"
  }
}
```

---

## 1.2 对话列表

```
GET /api/v1/conversations
```

返回当前学生的对话列表，按最近活跃排序。

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| context_type | string | 按场景类型筛选 |
| context_id | uuid | 按关联知识点/任务筛选 |
| status | string | `active` / `archived`，默认 `active` |
| keyword | string | 搜索对话标题或消息内容 |
| page | int | 页码，默认 1 |
| page_size | int | 每页条数，默认 20，最大 50 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "conv-uuid",
        "title": "有理数加减法不太懂",
        "context_type": "knowledge_point",
        "context_name": "有理数的加法",
        "status": "active",
        "message_count": 12,
        "last_message": {
          "role": "assistant",
          "content": "对的，你理解得很好！再试试这道题...",
          "created_at": "2026-03-25T19:15:00+08:00"
        },
        "created_at": "2026-03-25T19:00:00+08:00",
        "updated_at": "2026-03-25T19:15:00+08:00"
      }
    ],
    "total": 8,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 1.3 对话详情

```
GET /api/v1/conversations/:id
```

返回对话信息及完整消息历史。消息按时间正序排列。

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| message_limit | int | 加载最近 N 条消息，默认 50 |
| before_msg_id | uuid | 游标分页：加载此消息之前的记录 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "conv-uuid",
    "title": "有理数加减法不太懂",
    "context_type": "knowledge_point",
    "context_id": "kp-uuid-1",
    "context_name": "有理数的加法",
    "task_id": "task-uuid",
    "task_title": "第一章课后练习",
    "status": "active",
    "message_count": 12,
    "messages": [
      {
        "id": "msg-uuid-1",
        "role": "user",
        "content": "老师，有理数的加法法则是什么？",
        "created_at": "2026-03-25T19:00:00+08:00"
      },
      {
        "id": "msg-uuid-2",
        "role": "assistant",
        "content": "好问题！有理数的加法法则分三种情况...",
        "content_type": "text",
        "thinking_steps": ["理解学生问题", "检索知识点", "组织回答"],
        "knowledge_refs": [
          { "id": "kp-uuid-1", "name": "有理数的加法" }
        ],
        "token_usage": { "prompt": 320, "completion": 180 },
        "created_at": "2026-03-25T19:00:02+08:00"
      }
    ],
    "has_more": false,
    "created_at": "2026-03-25T19:00:00+08:00",
    "updated_at": "2026-03-25T19:15:00+08:00"
  }
}
```

---

## 1.4 删除对话

```
DELETE /api/v1/conversations/:id
```

软删除。学生只能删除自己的对话。

**Response** `200`

```json
{ "code": 0, "message": "ok", "data": null }
```
