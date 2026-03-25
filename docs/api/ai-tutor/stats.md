# 4. 统计分析

> 父文档：[README.md](./README.md)

---

## 4.1 我的辅导统计

```
GET /api/v1/tutor/stats
```

返回当前学生的 AI 辅导使用统计。

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| period | string | `today` / `week` / `month`，默认 `week` |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "period": "week",
    "total_conversations": 12,
    "total_messages": 86,
    "total_duration_minutes": 45,
    "avg_messages_per_conversation": 7.2,
    "top_knowledge_points": [
      { "id": "kp-uuid-1", "name": "有理数的加法", "count": 5 },
      { "id": "kp-uuid-3", "name": "有理数的乘法", "count": 3 },
      { "id": "kp-uuid-2", "name": "绝对值", "count": 2 }
    ],
    "feedback_summary": {
      "helpful": 8,
      "not_helpful": 1,
      "confusing": 1,
      "incorrect": 0
    },
    "daily_trend": [
      { "date": "2026-03-19", "conversations": 2, "messages": 14 },
      { "date": "2026-03-20", "conversations": 1, "messages": 8 },
      { "date": "2026-03-21", "conversations": 0, "messages": 0 },
      { "date": "2026-03-22", "conversations": 3, "messages": 22 },
      { "date": "2026-03-23", "conversations": 2, "messages": 16 },
      { "date": "2026-03-24", "conversations": 2, "messages": 12 },
      { "date": "2026-03-25", "conversations": 2, "messages": 14 }
    ]
  }
}
```

---

## 4.2 辅导使用概览（教师/管理员）

```
GET /api/v1/tutor/stats/overview
```

教师或管理员查看辅导系统整体使用情况。

**Query Params**

| 参数 | 类型 | 说明 |
|------|------|------|
| class_id | uuid | 按班级筛选 |
| grade | string | 按年级筛选（如 `grade_7`） |
| period | string | `today` / `week` / `month`，默认 `week` |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "period": "week",
    "active_students": 28,
    "total_students": 35,
    "usage_rate": 0.8,
    "total_conversations": 156,
    "total_messages": 1240,
    "avg_conversations_per_student": 5.6,
    "top_knowledge_points": [
      { "id": "kp-uuid-1", "name": "有理数的加法", "student_count": 18 },
      { "id": "kp-uuid-5", "name": "一元一次方程", "student_count": 12 }
    ],
    "struggling_students": [
      {
        "student_id": "student-uuid-1",
        "student_name": "李小华",
        "repeated_topics": ["有理数的减法", "绝对值"],
        "not_helpful_rate": 0.35,
        "suggestion": "该学生在有理数减法方面反复提问，建议教师关注"
      }
    ],
    "quality_metrics": {
      "helpful_rate": 0.85,
      "avg_response_time_ms": 2800,
      "total_token_cost_usd": 12.50
    }
  }
}
```

---

## 4.3 知识薄弱点分析

```
GET /api/v1/tutor/knowledge-gaps
```

基于对话历史分析当前学生的知识薄弱点。

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "gaps": [
      {
        "knowledge_point_id": "kp-uuid-4",
        "knowledge_point_name": "有理数的减法",
        "confidence_score": 0.35,
        "evidence": "多次重复提问同类问题，hint_level 逐步升高",
        "conversation_count": 4,
        "last_conversation_at": "2026-03-24T20:00:00+08:00",
        "recommendation": "建议回顾"有理数的减法"相关课时，重点理解减法转加法的转换"
      },
      {
        "knowledge_point_id": "kp-uuid-2",
        "knowledge_point_name": "绝对值",
        "confidence_score": 0.55,
        "evidence": "基本概念理解但应用题出错较多",
        "conversation_count": 2,
        "last_conversation_at": "2026-03-23T18:30:00+08:00",
        "recommendation": "基本概念已掌握，建议多做绝对值应用题练习"
      }
    ],
    "overall_mastery": 0.72,
    "analyzed_conversations": 12,
    "generated_at": "2026-03-25T19:00:00+08:00"
  }
}
```

**字段说明**

| 字段 | 说明 |
|------|------|
| confidence_score | 掌握程度 0-1，越低越薄弱 |
| evidence | AI 分析的判断依据 |
| recommendation | 针对性学习建议 |
| overall_mastery | 综合掌握水平 |
