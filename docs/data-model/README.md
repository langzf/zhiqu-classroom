# 数据模型

> 完整数据模型文档，按服务域拆分。

---

## 文档索引

| 文档 | 说明 | 状态 |
|------|------|------|
| [user-profile.md](./user-profile.md) | 用户域：users, student_profiles, guardian_bindings | ✅ |
| [course.md](./course.md) | 课程域：textbooks, knowledge_points, resources | ✅ |
| [learning-engine.md](./learning-engine.md) | 学习引擎：tasks, task_assignments, learning_records | ✅ |
| [ai-tutor.md](./ai-tutor.md) | AI 辅导：对话、消息 | ✅ |
| [analytics.md](./analytics.md) | 数据分析：学习报告、聚合统计 | ✅ |
| [llm-ops.md](./llm-ops.md) | LLM 运维：模型管理、路由、调用日志、用量统计 | ✅ |
| [platform.md](./platform.md) | 平台支撑：配置中心、审计日志、异步任务 | ✅ |

## 全局约定

### 主键

- 统一使用 **UUID v7**（时间有序，可排序）
- 字段名 `id`，类型 `UUID`

### 时间戳

- 所有表必须包含 `created_at TIMESTAMP NOT NULL` 和 `updated_at TIMESTAMP NOT NULL`
- 使用 UTC 存储，应用层转换时区

### 软删除

- 使用 `deleted_at TIMESTAMP NULL`（为 NULL 表示未删除）
- 查询默认过滤已删除记录

### 跨服务引用

- 使用 UUID 引用其他服务的实体，**不建立外键约束**
- 在字段注释中标明引用来源（如 `-- ref: users.id`）

### 字段类型风格

- PostgreSQL 原生类型：`VARCHAR`, `UUID`, `JSONB`, `TIMESTAMP`, `BOOLEAN`, `TEXT`, `INT`, `BIGINT`, `DECIMAL`
- 枚举值在应用层定义，数据库用 `VARCHAR`

### 索引命名

- 普通索引：`idx_{table}_{column}`
- 唯一索引：`uniq_{table}_{column}`
- 复合索引：`idx_{table}_{col1}_{col2}`

## ER 关系总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                          user-profile                                │
│  users ◄── student_profiles                                         │
│  users ◄── guardian_bindings ──► student_profiles                    │
└──────┬───────────────────────────────────────────────────────────────┘
       │ user_id
       ▼
┌──────────────────────┐     ┌──────────────────────────────────┐
│    learning-engine    │     │          course                   │
│  tasks ◄── assignments│     │  textbooks ◄── knowledge_points  │
│  learning_records     │     │  textbooks ◄── resources          │
└──────┬───────────────┘     └──────────────────────────────────┘
       │                              │
       │ task_id, user_id             │ textbook_id
       ▼                              ▼
┌──────────────────────┐     ┌──────────────────────────────────┐
│      ai-tutor         │     │          analytics                │
│  conversations        │     │  learning_reports                 │
│  messages             │     │  aggregate_stats                  │
└──────────────────────┘     └──────────────────────────────────┘
       │                              │
       │ llm calls                    │ data from
       ▼                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                            llm-ops                                    │
│  model_providers ◄── model_configs ◄── model_routing_rules           │
│  llm_call_logs    llm_usage_daily                                    │
└──────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           platform                                    │
│  sys_configs    audit_logs    async_tasks                             │
└──────────────────────────────────────────────────────────────────────┘
```
