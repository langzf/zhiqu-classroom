# 数据模型（MVP）

> 最后更新：2026-03-26  
> 参考: [MVP-SCOPE.md](../MVP-SCOPE.md)

---

## 文档索引（MVP）

| 文档 | 说明 | 表数 | 状态 |
|------|------|------|------|
| [user-profile.md](./user-profile.md) | 用户域：users, student_profiles, oauth_bindings, guardian_bindings | 4 | ✅ |
| [course.md](./course.md) | 教材域：textbooks, chapters, knowledge_points, kp_embeddings, generated_resources, prompt_templates | 6 | ✅ |
| [ai-tutor.md](./ai-tutor.md) | AI 辅导域：conversations, messages | 2 | ✅ |

**MVP 总计：~12 张核心表**（learning-core 的 3 张表在开发时按需补充）

## 归档的数据模型

以下已移至 `archive/data-model/`：

- `learning-engine.md` — 完整学习引擎（4 表）→ MVP 用简化版
- `analytics.md` — 分析域（报告、聚合统计）
- `llm-ops.md` — LLM 运维（5 表）
- `platform/` — 平台支撑（配置中心、审计、异步任务、通知，共 8 表）

## 全局约定

### 主键
- 统一 **UUID v7**（时间有序），字段名 `id`

### 时间戳
- 必须包含 `created_at TIMESTAMP NOT NULL` 和 `updated_at TIMESTAMP NOT NULL`
- UTC 存储，应用层转换时区

### 软删除
- `deleted_at TIMESTAMP NULL`（NULL = 未删除）

### 跨服务引用
- UUID 引用，**不建外键约束**
- 字段注释标明来源：`-- ref: users.id`

### 字段类型
- PostgreSQL 原生类型：`VARCHAR`, `UUID`, `JSONB`, `TIMESTAMP`, `BOOLEAN`, `TEXT`, `INT`, `BIGINT`, `DECIMAL`
- 枚举值应用层定义，数据库用 `VARCHAR`

### 索引命名
- 普通索引：`idx_{table}_{column}`
- 唯一索引：`uniq_{table}_{column}`
- 复合索引：`idx_{table}_{col1}_{col2}`

## ER 关系总览（MVP）

```
┌──────────────────────────────────────────────────────┐
│                    user-profile                       │
│  users ◄── student_profiles                          │
│  users ◄── user_oauth_bindings                       │
│  users ◄── guardian_bindings ──► users (student)     │
└──────┬───────────────────────────────────────────────┘
       │ user_id (UUID, 无外键)
       ▼
┌──────────────────────┐     ┌─────────────────────────┐
│    learning-core      │     │     content-engine       │
│  tasks (简化)         │     │  textbooks ◄── chapters  │
│  task_assignments     │     │  chapters ◄── kpoints    │
│  progress_records     │     │  kpoints ◄── embeddings  │
└──────────────────────┘     │  generated_resources     │
       │                      │  prompt_templates        │
       │                      └─────────────────────────┘
       │ user_id, task_id             │ kp_id
       ▼                              ▼
┌──────────────────────────────────────────────────────┐
│                      ai-tutor                         │
│  conversations ◄── messages                           │
│  (RAG 检索 kp_embeddings)                             │
└──────────────────────────────────────────────────────┘
```
