# Analytics & Reporting API — 统计报表 + 通知

> 父文档：[README.md](./README.md) | 数据模型：[data-model.md](../data-model.md) analytics-reporting schema  
> 服务前缀：`/api/v1`

---

## 接口总览

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| GET | `/analytics/daily-stats` | 👤 student/guardian | 每日学习统计 |
| GET | `/analytics/daily-stats/trend` | 👤 student/guardian | 学习趋势（多天） |
| GET | `/analytics/weekly-reports` | 👤 student/guardian | 周报列表 |
| GET | `/analytics/weekly-reports/:id` | 👤 student/guardian | 周报详情 |
| POST | `/analytics/weekly-reports/generate` | 🤖 system/admin | 手动触发生成周报 |
| GET | `/analytics/knowledge-mastery` | 👤 student/guardian | 知识点掌握度 |
| GET | `/analytics/content-usage` | 🛡️ admin | 内容使用统计 |
| GET | `/analytics/overview` | 🛡️ admin | 平台数据概览 |
| GET | `/notifications` | 👤 all | 通知列表 |
| GET | `/notifications/unread-count` | 👤 all | 未读通知数 |
| PATCH | `/notifications/:id/read` | 👤 all | 标记已读 |
| POST | `/notifications/read-all` | 👤 all | 全部标记已读 |

共 **12** 个接口。

---

## 1. 每日学习统计

### 1.1 查询每日学习统计

```
GET /api/v1/analytics/daily-stats
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | UUID | 条件 | 学生 ID（家长查看孩子时必传，学生默认自己） |
| date | DATE | 否 | 查询日期，默认今天，格式 `YYYY-MM-DD` |

**权限说明**
- 学生：只能查自己，不传 `student_id`
- 家长：必须传 `student_id`，且该学生已通过 `guardian_bindings` 绑定且 `verified = true`

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "student_user_id": "...",
    "stat_date": "2026-03-25",
    "study_duration_sec": 3600,
    "tasks_completed": 3,
    "resources_completed": 5,
    "games_played": 2,
    "videos_watched": 1,
    "practices_done": 2,
    "avg_accuracy": 0.82,
    "knowledge_points_covered": 8
  }
}
```

**Response 404** — 当天无学习数据

```json
{
  "code": 41001,
  "message": "该日期暂无学习数据"
}
```

---

### 1.2 学习趋势

```
GET /api/v1/analytics/daily-stats/trend
```

返回一段时间内的每日统计数组，用于趋势图展示。

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | UUID | 条件 | 同上 |
| start_date | DATE | 是 | 起始日期（含） |
| end_date | DATE | 是 | 结束日期（含），最大跨度 90 天 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "student_user_id": "...",
    "start_date": "2026-03-01",
    "end_date": "2026-03-25",
    "daily": [
      {
        "stat_date": "2026-03-01",
        "study_duration_sec": 2400,
        "tasks_completed": 2,
        "avg_accuracy": 0.75,
        "knowledge_points_covered": 5
      },
      {
        "stat_date": "2026-03-02",
        "study_duration_sec": 3600,
        "tasks_completed": 3,
        "avg_accuracy": 0.80,
        "knowledge_points_covered": 7
      }
    ],
    "summary": {
      "total_days": 25,
      "active_days": 18,
      "total_duration_sec": 64800,
      "total_tasks_completed": 42,
      "avg_accuracy": 0.78
    }
  }
}
```

---

## 2. 周报

### 2.1 周报列表

```
GET /api/v1/analytics/weekly-reports
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | UUID | 条件 | 同上 |
| page | INT | 否 | 页码，默认 1 |
| page_size | INT | 否 | 每页条数，默认 10，最大 50 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "...",
        "week_start": "2026-03-16",
        "week_end": "2026-03-22",
        "generated_at": "2026-03-23T08:00:00Z",
        "summary": {
          "active_days": 5,
          "total_duration_min": 240,
          "tasks_completed": 8,
          "avg_accuracy": 0.81
        }
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 10
  }
}
```

---

### 2.2 周报详情

```
GET /api/v1/analytics/weekly-reports/:id
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "...",
    "student_user_id": "...",
    "week_start": "2026-03-16",
    "week_end": "2026-03-22",
    "generated_at": "2026-03-23T08:00:00Z",
    "sent_to_parent": true,
    "report_data": {
      "summary": {
        "active_days": 5,
        "total_duration_min": 240,
        "tasks_completed": 8,
        "avg_accuracy": 0.81
      },
      "subject_breakdown": [
        {
          "subject": "math",
          "duration_min": 160,
          "accuracy": 0.78,
          "kp_mastered": ["kp_uuid_001", "kp_uuid_003"],
          "kp_weak": ["kp_uuid_005"]
        },
        {
          "subject": "physics",
          "duration_min": 80,
          "accuracy": 0.86,
          "kp_mastered": ["kp_uuid_010"],
          "kp_weak": []
        }
      ],
      "highlights": [
        "连续5天完成课后任务",
        "一元二次方程正确率提升15%"
      ],
      "suggestions": [
        "建议加强判别式应用题练习",
        "物理力学部分可以尝试进阶难度"
      ]
    }
  }
}
```

---

### 2.3 手动触发生成周报

```
POST /api/v1/analytics/weekly-reports/generate
```

通常由定时任务每周一自动触发。此接口供管理员手动补生成。

**Request Body**

```json
{
  "student_id": "...",
  "week_start": "2026-03-16"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | UUID | 否 | 不传则为所有学生生成 |
| week_start | DATE | 是 | 周一日期 |

**Response 202** — 异步任务已提交

```json
{
  "code": 0,
  "message": "周报生成任务已提交",
  "data": {
    "task_id": "...",
    "estimated_count": 156
  }
}
```

---

## 3. 知识点掌握度

### 3.1 查询知识点掌握度

```
GET /api/v1/analytics/knowledge-mastery
```

基于学生的学习记录和练习正确率，聚合计算每个知识点的掌握等级。

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| student_id | UUID | 条件 | 同上 |
| textbook_id | UUID | 否 | 按教材筛选 |
| chapter_id | UUID | 否 | 按章节筛选 |
| mastery_level | STRING | 否 | 筛选掌握等级：`mastered` / `learning` / `weak` |
| page | INT | 否 | 页码，默认 1 |
| page_size | INT | 否 | 每页条数，默认 20，最大 100 |

**掌握等级计算规则**（应用层）

| 等级 | 条件 |
|------|------|
| `mastered` | 正确率 ≥ 80% 且练习次数 ≥ 3 |
| `learning` | 正确率 50%~79% 或练习次数 < 3 |
| `weak` | 正确率 < 50% |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "knowledge_point_id": "...",
        "knowledge_point_name": "一元二次方程的判别式",
        "chapter_name": "一元二次方程",
        "textbook_name": "人教版数学七年级上",
        "mastery_level": "learning",
        "accuracy": 0.65,
        "practice_count": 4,
        "last_practiced_at": "2026-03-24T15:30:00Z"
      }
    ],
    "total": 48,
    "page": 1,
    "page_size": 20,
    "summary": {
      "total_kp": 48,
      "mastered": 20,
      "learning": 18,
      "weak": 10
    }
  }
}
```

---

## 4. 内容使用统计（管理员）

### 4.1 查询内容使用统计

```
GET /api/v1/analytics/content-usage
```

统计各资源 / 知识点的使用情况，帮助运营了解内容质量和热度。

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| resource_type | STRING | 否 | 资源类型筛选 |
| knowledge_point_id | UUID | 否 | 知识点筛选 |
| start_date | DATE | 是 | 起始日期 |
| end_date | DATE | 是 | 结束日期，最大跨度 90 天 |
| sort_by | STRING | 否 | 排序字段：`total_views` / `avg_accuracy` / `total_completions`，默认 `total_views` |
| sort_order | STRING | 否 | `asc` / `desc`，默认 `desc` |
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
        "resource_id": "...",
        "resource_type": "game_quiz",
        "knowledge_point_id": "...",
        "knowledge_point_name": "勾股定理",
        "total_views": 1250,
        "total_completions": 980,
        "completion_rate": 0.78,
        "avg_accuracy": 0.72,
        "avg_duration_sec": 300
      }
    ],
    "total": 156,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 5. 平台数据概览（管理员）

### 5.1 概览看板

```
GET /api/v1/analytics/overview
```

管理后台首页看板数据。

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | STRING | 否 | 时间范围：`today` / `week` / `month`，默认 `today` |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "users": {
      "total_students": 1580,
      "total_guardians": 620,
      "new_registrations": 23,
      "daily_active": 456
    },
    "learning": {
      "total_study_duration_sec": 1620000,
      "total_tasks_completed": 3200,
      "avg_accuracy": 0.76,
      "avg_daily_duration_min": 35
    },
    "content": {
      "total_textbooks": 12,
      "total_knowledge_points": 860,
      "total_resources": 2400,
      "resources_by_type": {
        "game_quiz": 800,
        "game_drag_match": 600,
        "video_script": 500,
        "practice_set": 500
      }
    },
    "llm": {
      "total_calls_today": 4500,
      "total_cost_today_yuan": 128.50,
      "avg_latency_ms": 2300
    }
  }
}
```

---

## 6. 通知

站内通知系统。MVP 阶段仅支持站内消息推送（App 内通知列表 + 角标），后续可接入微信模板消息、短信等渠道。

### 通知触发场景

| 触发事件 | 接收者 | 通知内容 |
|----------|--------|----------|
| 周报生成完成 | 学生 + 家长 | "本周学习报告已生成，点击查看" |
| 任务分配 | 学生 | "你有一个新任务：{task_name}" |
| 任务即将截止 | 学生 | "任务 {task_name} 将于明天截止" |
| 学生完成任务 | 家长 | "{student_name} 完成了任务 {task_name}" |
| 学习成就达成 | 学生 | "恭喜！你已连续学习7天" |

---

### 6.1 通知列表

```
GET /api/v1/notifications
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_read | BOOLEAN | 否 | 筛选已读/未读 |
| type | STRING | 否 | 通知类型：`report` / `task` / `achievement` / `system` |
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
        "type": "report",
        "title": "本周学习报告已生成",
        "content": "你本周累计学习 4 小时，完成 8 个任务，平均正确率 81%。点击查看详情。",
        "is_read": false,
        "action_url": "/weekly-reports/xxx",
        "created_at": "2026-03-23T08:00:00Z"
      },
      {
        "id": "...",
        "type": "task",
        "title": "新任务：一元二次方程课后练习",
        "content": "老师布置了一个新任务，截止时间 2026-03-26。",
        "is_read": true,
        "action_url": "/tasks/xxx",
        "created_at": "2026-03-22T10:00:00Z"
      }
    ],
    "total": 36,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 6.2 未读通知数

```
GET /api/v1/notifications/unread-count
```

轻量接口，用于首页角标展示。

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "unread_count": 3
  }
}
```

---

### 6.3 标记单条已读

```
PATCH /api/v1/notifications/:id/read
```

**Response 200**

```json
{
  "code": 0,
  "message": "ok"
}
```

---

### 6.4 全部标记已读

```
POST /api/v1/notifications/read-all
```

**Request Body**（可选）

```json
{
  "type": "task"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | STRING | 否 | 只标记某一类型为已读，不传则全部标记 |

**Response 200**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "marked_count": 3
  }
}
```

---

## 7. 错误码

| 错误码 | 说明 |
|--------|------|
| 41001 | 该日期暂无学习数据 |
| 41002 | 周报不存在 |
| 41003 | 无权查看该学生数据（家长未绑定 / 未验证） |
| 41004 | 日期跨度超出限制（最大 90 天） |
| 41005 | 通知不存在 |
| 41006 | 周报生成任务提交失败 |

---

## 8. 数据生成机制说明

### 8.1 每日统计

- **来源**：聚合 `learning_records` 表当天数据
- **触发**：每日凌晨 01:00 定时任务；也支持实时增量更新（学习记录提交时异步刷新）
- **幂等**：基于 `(student_user_id, stat_date)` 唯一约束，重复执行只更新不重复插入

### 8.2 周报

- **来源**：聚合该周 `daily_study_stats` + `learning_records`；`highlights` 和 `suggestions` 由 LLM 生成
- **触发**：每周一 08:00 定时任务；支持管理员手动触发
- **推送**：生成后通过通知系统推送给学生和已绑定家长
- **LLM 调用**：task_type = `report_generate`，输入为该周学习数据的结构化摘要

### 8.3 内容使用统计

- **来源**：聚合 `learning_records` 按资源维度
- **触发**：每日凌晨 02:00 定时任务
- **用途**：运营侧内容质量分析，辅助决策哪些内容需要优化