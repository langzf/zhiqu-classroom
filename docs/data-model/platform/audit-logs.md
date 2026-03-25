# 审计日志

> Schema: `platform`
> 最后更新: 2026-03-25

---

## 概述

审计日志记录所有管理员操作和敏感数据变更，用于安全审计、合规追溯和故障排查。
采用追加写入（append-only）模式，**不可修改、不可删除**。

---

## 1. audit_logs（审计日志）

### DDL

```sql
CREATE TABLE platform.audit_logs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    action          VARCHAR(50)     NOT NULL,
    resource_type   VARCHAR(50)     NOT NULL,
    resource_id     UUID            NULL,
    operator_id     UUID            NOT NULL,       -- ref: users.id
    operator_role   VARCHAR(20)     NOT NULL,
    operator_ip     VARCHAR(45)     NULL,
    user_agent      VARCHAR(500)    NULL,
    request_method  VARCHAR(10)     NULL,
    request_path    VARCHAR(500)    NULL,
    changes         JSONB           NULL,
    metadata        JSONB           NULL,
    trace_id        VARCHAR(64)     NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT now()
);
-- 注意：无 updated_at / deleted_at — 审计日志 append-only
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 日志 ID |
| action | VARCHAR(50) | NOT NULL | 操作类型：`create` / `update` / `delete` / `login` / `export` / `config_change` / `role_change` |
| resource_type | VARCHAR(50) | NOT NULL | 资源类型：`user` / `textbook` / `task` / `sys_config` / `model_config` / `notification_template` |
| resource_id | UUID | NULL | 操作对象 ID（登录等无资源操作可为 NULL） |
| operator_id | UUID | NOT NULL | 操作人 — ref: users.id |
| operator_role | VARCHAR(20) | NOT NULL | 操作时的角色：`admin` / `teacher` |
| operator_ip | VARCHAR(45) | NULL | 客户端 IP（支持 IPv6） |
| user_agent | VARCHAR(500) | NULL | 客户端 UA |
| request_method | VARCHAR(10) | NULL | HTTP 方法：GET / POST / PUT / DELETE |
| request_path | VARCHAR(500) | NULL | 请求路径 |
| changes | JSONB | NULL | 变更详情 `{"before": {...}, "after": {...}}` |
| metadata | JSONB | NULL | 附加上下文（如批量操作的 ID 列表） |
| trace_id | VARCHAR(64) | NULL | 链路追踪 ID，关联请求日志 |
| created_at | TIMESTAMP | NOT NULL | 操作时间 |

### 索引

```sql
-- 按资源查审计记录
CREATE INDEX idx_audit_logs_resource
    ON platform.audit_logs (resource_type, resource_id, created_at DESC);

-- 按操作人查
CREATE INDEX idx_audit_logs_operator
    ON platform.audit_logs (operator_id, created_at DESC);

-- 按操作类型 + 时间
CREATE INDEX idx_audit_logs_action
    ON platform.audit_logs (action, created_at DESC);

-- 按时间范围查（管理后台分页）
CREATE INDEX idx_audit_logs_created
    ON platform.audit_logs (created_at DESC);

-- trace_id 关联
CREATE INDEX idx_audit_logs_trace
    ON platform.audit_logs (trace_id)
    WHERE trace_id IS NOT NULL;
```

### changes 字段示例

```json
{
  "before": {
    "role": "student",
    "status": "active"
  },
  "after": {
    "role": "teacher",
    "status": "active"
  }
}
```

---

## 数据保留策略

| 策略 | 说明 |
|------|------|
| 在线保留 | 90 天（PostgreSQL） |
| 归档存储 | 90 天后导出至对象存储（MinIO `exports` bucket） |
| 永久保留 | 角色变更、用户删除等关键操作永久不删 |

### 归档 SQL 示例

```sql
-- 导出 90 天前的审计日志（应用层执行后写入 MinIO）
SELECT * FROM platform.audit_logs
WHERE created_at < now() - INTERVAL '90 days'
ORDER BY created_at;

-- 归档后删除（仅非关键操作）
DELETE FROM platform.audit_logs
WHERE created_at < now() - INTERVAL '90 days'
  AND action NOT IN ('role_change', 'delete');
```

---

## 枚举值

| 枚举名 | 值 | 说明 |
|--------|-----|------|
| audit_action | `create`, `update`, `delete`, `login`, `logout`, `export`, `config_change`, `role_change`, `permission_change` | 操作类型 |
| resource_type | `user`, `textbook`, `knowledge_point`, `resource`, `task`, `sys_config`, `model_config`, `notification_template` | 资源类型 |

---

## 使用场景

### 查看某教材的所有操作

```sql
SELECT action, operator_id, changes, created_at
FROM platform.audit_logs
WHERE resource_type = 'textbook'
  AND resource_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY created_at DESC;
```

### 查看某管理员近 7 天操作

```sql
SELECT action, resource_type, resource_id, changes, created_at
FROM platform.audit_logs
WHERE operator_id = '550e8400-e29b-41d4-a716-446655440001'
  AND created_at > now() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

### 统计各操作类型分布

```sql
SELECT action, COUNT(*) AS cnt
FROM platform.audit_logs
WHERE created_at > now() - INTERVAL '30 days'
GROUP BY action
ORDER BY cnt DESC;
```

---

## 日志关联

审计日志与 [logging-design.md](../../logging-design.md) 中的结构化日志通过 `trace_id` 关联：

- **审计日志（audit_logs）**：持久化到 PostgreSQL，用于合规查询
- **结构化日志（Loki/ELK）**：包含完整请求上下文，用于调试排查
- 通过 `trace_id` 可从审计记录跳转到完整请求链路
