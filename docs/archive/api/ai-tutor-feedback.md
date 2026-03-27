# 3. 反馈

> 父文档：[README.md](./README.md)

---

## 3.1 对话反馈

```
POST /api/v1/conversations/:id/feedback
```

学生可对整轮对话或单条消息给出反馈，用于改进 AI 质量。

**Request Body**

```json
{
  "message_id": "msg-uuid-4",
  "rating": "helpful",
  "comment": "解释得很清楚，我懂了"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message_id | uuid | | 针对某条消息，不填则针对整个对话 |
| rating | string | ✅ | `helpful` / `not_helpful` / `confusing` / `incorrect` |
| comment | string | | 补充说明，最长 500 字 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "feedback-uuid",
    "conversation_id": "conv-uuid",
    "message_id": "msg-uuid-4",
    "rating": "helpful",
    "comment": "解释得很清楚，我懂了",
    "created_at": "2026-03-25T19:10:00+08:00"
  }
}
```

**业务规则**

- 每个 `message_id` 只能反馈一次（重复提交返回 `50009`）
- 对话级反馈（不带 `message_id`）同样只能提交一次
- 反馈数据用于：
  - 统计 AI 回复质量（helpful_rate）
  - 识别 struggling students（not_helpful 占比高的学生）
  - 改进系统提示词和知识检索策略
