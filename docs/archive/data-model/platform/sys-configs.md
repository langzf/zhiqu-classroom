# 系统配置中心

> Schema: `platform`
> 最后更新: 2026-03-25

---

## 概述

系统配置中心提供运行时配置管理能力，支持功能开关、参数调优、限流阈值等动态配置。
配置项按 `config_group` 分组，支持变更审计追踪。

---

## 1. sys_configs（系统配置项）

存储全局配置 KV 对，支持运行时热更新。

### DDL

```sql
CREATE TABLE platform.sys_configs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key      VARCHAR(200)    NOT NULL,
    config_value    TEXT            NOT NULL,
    value_type      VARCHAR(20)     NOT NULL DEFAULT 'string',
    config_group    VARCHAR(50)     NOT NULL DEFAULT 'general',
    description     VARCHAR(500)    NULL,
    is_sensitive    BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMP       NULL
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 配置 ID |
| config_key | VARCHAR(200) | NOT NULL | 配置键，如 `sms.daily_limit`、`llm.default_model` |
| config_value | TEXT | NOT NULL | 配置值（JSON / 字符串 / 数字） |
| value_type | VARCHAR(20) | NOT NULL | 值类型：`string` / `number` / `boolean` / `json` |
| config_group | VARCHAR(50) | NOT NULL | 分组：`general` / `sms` / `llm` / `security` / `feature_flag` |
| description | VARCHAR(500) | NULL | 人类可读说明 |
| is_sensitive | BOOLEAN | NOT NULL | 是否敏感配置（敏感值读取时脱敏） |
| is_active | BOOLEAN | NOT NULL | 是否启用 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |
| deleted_at | TIMESTAMP | NULL | 软删除 |

### 索引

```sql
-- 配置键唯一（未删除）
CREATE UNIQUE INDEX uniq_sys_configs_key
    ON platform.sys_configs (config_key)
    WHERE deleted_at IS NULL;

-- 按分组查询
CREATE INDEX idx_sys_configs_group
    ON platform.sys_configs (config_group)
    WHERE deleted_at IS NULL;
```

### 初始数据示例

```sql
INSERT INTO platform.sys_configs (config_key, config_value, value_type, config_group, description) VALUES
-- 短信限流
('sms.daily_limit_per_phone',    '10',           'number',  'sms',          '单手机号每日短信上限'),
('sms.cooldown_seconds',         '60',           'number',  'sms',          '短信发送冷却时间(秒)'),
-- LLM
('llm.default_model',            'gpt-4o',       'string',  'llm',          '默认 LLM 模型'),
('llm.max_tokens_chat',          '4096',         'number',  'llm',          '对话最大 token 数'),
('llm.temperature_default',      '0.7',          'number',  'llm',          '默认 temperature'),
-- 功能开关
('feature.ai_tutor_enabled',     'true',         'boolean', 'feature_flag', 'AI 辅导功能总开关'),
('feature.wechat_login_enabled', 'true',         'boolean', 'feature_flag', '微信登录开关'),
('feature.auto_review_enabled',  'false',        'boolean', 'feature_flag', '自动审核开关（MVP 关闭）'),
-- 安全
('security.login_max_attempts',  '5',            'number',  'security',     '登录最大失败次数/小时'),
('security.jwt_access_ttl',      '7200',         'number',  'security',     'Access Token 有效期(秒)');
```

### 缓存策略

- Redis 缓存：`sys_config:{config_key}` → config_value
- TTL: 5 分钟
- 更新时主动失效缓存

---

## 2. sys_config_history（配置变更历史）

记录每次配置变更的完整快照，用于审计和回滚。

### DDL

```sql
CREATE TABLE platform.sys_config_history (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id       UUID            NOT NULL,       -- ref: sys_configs.id
    config_key      VARCHAR(200)    NOT NULL,
    old_value       TEXT            NULL,
    new_value       TEXT            NOT NULL,
    change_reason   VARCHAR(500)    NULL,
    operator_id     UUID            NOT NULL,       -- ref: users.id
    created_at      TIMESTAMP       NOT NULL DEFAULT now()
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| config_id | UUID | NOT NULL | 关联 sys_configs.id |
| config_key | VARCHAR(200) | NOT NULL | 冗余配置键（便于查询） |
| old_value | TEXT | NULL | 变更前的值（首次创建为 NULL） |
| new_value | TEXT | NOT NULL | 变更后的值 |
| change_reason | VARCHAR(500) | NULL | 变更原因 |
| operator_id | UUID | NOT NULL | 操作人 — ref: users.id |
| created_at | TIMESTAMP | NOT NULL | 变更时间 |

### 索引

```sql
-- 按配置项查变更历史
CREATE INDEX idx_config_history_config_id
    ON platform.sys_config_history (config_id, created_at DESC);

-- 按操作人查
CREATE INDEX idx_config_history_operator
    ON platform.sys_config_history (operator_id, created_at DESC);
```

---

## 枚举值

| 枚举名 | 值 | 使用字段 |
|--------|-----|----------|
| value_type | `string`, `number`, `boolean`, `json` | sys_configs.value_type |
| config_group | `general`, `sms`, `llm`, `security`, `feature_flag`, `notification`, `media` | sys_configs.config_group |

---

## 使用场景

### 功能开关查询

```sql
-- 检查 AI 辅导是否启用
SELECT config_value::boolean
FROM platform.sys_configs
WHERE config_key = 'feature.ai_tutor_enabled'
  AND is_active = TRUE
  AND deleted_at IS NULL;
```

### 查看某配置的变更历史

```sql
SELECT h.old_value, h.new_value, h.change_reason, h.created_at
FROM platform.sys_config_history h
WHERE h.config_key = 'llm.default_model'
ORDER BY h.created_at DESC
LIMIT 10;
```
