# 5. 服务间接口（Internal）

> 父文档：[README.md](./README.md)
> 以下接口仅供内部服务调用，不通过 api-gateway 对外暴露。

---

## 5.1 获取知识点上下文

```
GET /internal/knowledge-context/:kpId
```

ai-tutor 调用 content-engine 获取知识点的完整上下文（用于构建 LLM prompt）。

**调用方向**：`ai-tutor → content-engine`

**Response** `200`

```json
{
  "knowledge_point": {
    "id": "kp-uuid-1",
    "name": "有理数的加法",
    "description": "有理数加法的运算法则，包括同号相加和异号相加",
    "textbook_content": "有理数的加法法则：\n1. 同号两数相加，取相同的符号...",
    "prerequisites": ["绝对值", "正数与负数"],
    "difficulty_level": 2,
    "chapter_path": ["第一章 有理数", "1.3 有理数的加减法"],
    "embeddings_available": true
  }
}
```

---

## 5.2 记录学习事件

```
POST /internal/learning-events
```

ai-tutor 向 learning-orchestrator 上报学习事件，用于更新学习记录和统计。

**调用方向**：`ai-tutor → learning-orchestrator`

**Request Body**

```json
{
  "student_id": "student-uuid",
  "event_type": "tutor_conversation",
  "conversation_id": "conv-uuid",
  "knowledge_point_ids": ["kp-uuid-1"],
  "metrics": {
    "message_count": 8,
    "hint_count": 2,
    "max_hint_level": 2,
    "feedback_rating": "helpful",
    "duration_seconds": 300,
    "estimated_mastery_delta": 0.1
  },
  "timestamp": "2026-03-25T19:15:00+08:00"
}
```

| 字段 | 说明 |
|------|------|
| event_type | 固定 `tutor_conversation` |
| metrics.hint_count | 本次对话请求提示的次数 |
| metrics.max_hint_level | 最高提示级别（1-3） |
| metrics.estimated_mastery_delta | 预估掌握度变化（正为提升，负为下降） |

**Response** `202 Accepted`

---

## 5.3 对话完成事件

当对话结束（超过 30 分钟无新消息 / 学生主动结束）时，ai-tutor 发布 Redis Stream 事件。

**Stream**：`stream:conversation.completed`

**Payload**

```json
{
  "event_id": "evt-uuid",
  "event_name": "conversation.completed",
  "occurred_at": "2026-03-25T19:15:00+08:00",
  "producer": "ai-tutor",
  "payload": {
    "conversation_id": "conv-uuid",
    "student_id": "student-uuid",
    "summary": "学生学习了有理数的加法法则，掌握了同号相加的规则，异号相加还需练习",
    "knowledge_points_covered": ["kp-uuid-1"],
    "mastery_assessment": {
      "kp-uuid-1": {
        "before": 0.3,
        "after": 0.55,
        "confidence": "medium"
      }
    },
    "total_messages": 12,
    "duration_minutes": 15
  }
}
```

**消费者**

| 服务 | 行为 |
|------|------|
| `learning-orchestrator` | 更新学生知识点掌握度，调整学习路径 |
| `analytics-reporting` | 汇入辅导统计报表 |
| `notification` | 如配置了学习报告推送，触发家长通知 |

---

## 5.4 相似知识点检索（向量）

```
POST /internal/knowledge-search
```

ai-tutor 通过语义搜索查找与学生提问最相关的知识点，辅助精准回答。

**调用方向**：`ai-tutor → content-engine`

**Request Body**

```json
{
  "query": "负数加负数怎么算",
  "textbook_id": "tb-uuid",
  "top_k": 5,
  "min_score": 0.7
}
```

**Response** `200`

```json
{
  "results": [
    {
      "knowledge_point_id": "kp-uuid-1",
      "name": "有理数的加法",
      "score": 0.92,
      "snippet": "同号两数相加，取相同的符号，并把绝对值相加..."
    },
    {
      "knowledge_point_id": "kp-uuid-4",
      "name": "有理数的减法",
      "score": 0.78,
      "snippet": "减去一个数，等于加上这个数的相反数..."
    }
  ]
}
```
