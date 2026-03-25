# 平台支撑数据模型

> Schema: `platform` / `notification`
> 最后更新: 2026-03-25

---

## 概述

平台支撑域提供跨业务的通用基础能力，包括系统配置管理、操作审计、异步任务调度和消息通知触达。
这些表不属于任何单一业务服务，而是为整个平台提供底层支撑。

## 文档索引

| 文档 | Schema | 说明 | 表数量 |
|------|--------|------|--------|
| [sys-configs.md](./sys-configs.md) | `platform` | 系统配置中心：功能开关、参数调优、运行时配置 | 2 |
| [audit-logs.md](./audit-logs.md) | `platform` | 操作审计日志：管理员操作、敏感数据变更追踪 | 1 |
| [async-tasks.md](./async-tasks.md) | `platform` | 异步任务管理：教材解析、报告生成等后台任务 | 2 |
| [notification.md](./notification.md) | `notification` | 消息通知触达：短信、微信、站内信模板与发送记录 | 3 |

## 表一览

| 表名 | Schema | 说明 | 预估行量(MVP) |
|------|--------|------|---------------|
| `sys_configs` | platform | 系统配置项 | ~100 |
| `sys_config_history` | platform | 配置变更历史 | ~500 |
| `audit_logs` | platform | 审计日志 | ~10K/月 |
| `async_tasks` | platform | 异步任务主表 | ~5K/月 |
| `async_task_logs` | platform | 任务执行日志 | ~15K/月 |
| `notification_templates` | notification | 通知模板 | ~50 |
| `notification_logs` | notification | 发送记录 | ~20K/月 |
| `notification_preferences` | notification | 用户通知偏好 | ~500 |

## Schema 初始化

```sql
CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS notification;
```

## ER 关系

```
platform schema
┌───────────────────────────────────────────────────────┐
│                                                       │
│  sys_configs ◄── sys_config_history                   │
│     (配置项)       (变更历史)                           │
│                                                       │
│  audit_logs                                           │
│     (审计日志，独立表，无外键)                           │
│                                                       │
│  async_tasks ◄── async_task_logs                      │
│     (任务主表)      (执行日志)                          │
│                                                       │
└───────────────────────────────────────────────────────┘

notification schema
┌───────────────────────────────────────────────────────┐
│                                                       │
│  notification_templates ◄── notification_logs         │
│     (消息模板)                  (发送记录)              │
│                                                       │
│  notification_preferences                             │
│     (用户通知偏好，ref: users.id)                      │
│                                                       │
└───────────────────────────────────────────────────────┘
```

## 跨服务引用

| 引用字段 | 来源 | 说明 |
|----------|------|------|
| `audit_logs.operator_id` | `user_profile.users.id` | 操作人 |
| `async_tasks.created_by` | `user_profile.users.id` | 任务创建者 |
| `notification_logs.user_id` | `user_profile.users.id` | 接收人 |
| `notification_preferences.user_id` | `user_profile.users.id` | 偏好所有者 |
| `async_tasks.resource_id` | 各服务实体 ID | 关联的业务资源 |

> 跨服务引用只存 UUID，不建外键约束。
