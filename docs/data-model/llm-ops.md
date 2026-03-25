# LLM 运维域数据模型

> 对应服务：平台层 / `llm-gateway`
> Schema 隔离：`llm_ops`

---

## 概述

LLM 运维域管理模型提供商、模型配置、路由规则、调用日志和用量统计。支撑多模型统一调度、成本控制、熔断降级等运维需求。

### 表清单

| 表名 | 说明 | 预估行数 |
|------|------|----------|
| `model_providers` | 模型提供商 | 十级 |
| `model_configs` | 模型配置 | 百级 |
| `model_routing_rules` | 路由规则 | 百级 |
| `llm_call_logs` | 调用日志 | 百万级 |
| `llm_usage_daily` | 每日用量统计 | 万级 |

---

## 1. model_providers — 模型提供商

```sql
CREATE TABLE model_providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(50)  NOT NULL UNIQUE,    -- 提供商标识：deepseek / openai / anthropic / qwen
    display_name    VARCHAR(100) NOT NULL,           -- 显示名称
    base_url        VARCHAR(500) NOT NULL,           -- API 基础地址
    api_key_encrypted VARCHAR(1000) NOT NULL,        -- AES 加密后的 API Key
    api_version     VARCHAR(30),                     -- API 版本号
    status          VARCHAR(20)  NOT NULL DEFAULT 'active',
                                                     -- active / disabled
    rate_limit_rpm  INT,                             -- 全局限速（请求/分钟）
    rate_limit_tpm  INT,                             -- 全局限速（Token/分钟）
    config          JSONB        NOT NULL DEFAULT '{}',
                                                     -- 提供商级别配置
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);
```

### config JSONB Schema

```json
{
  "timeout_sec": 60,
  "max_retries": 3,
  "retry_backoff_sec": [1, 2, 4],
  "custom_headers": {
    "X-Custom-Header": "value"
  },
  "proxy_url": null
}
```

---

## 2. model_configs — 模型配置

```sql
CREATE TABLE model_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id     UUID         NOT NULL,           -- ref: model_providers.id
    model_name      VARCHAR(100) NOT NULL,           -- 模型标识：deepseek-chat / gpt-4o
    display_name    VARCHAR(100) NOT NULL,
    model_type      VARCHAR(30)  NOT NULL DEFAULT 'chat',
                                                     -- chat / embedding / vision
    status          VARCHAR(20)  NOT NULL DEFAULT 'active',
                                                     -- active / disabled / deprecated
    is_default      BOOLEAN      NOT NULL DEFAULT false,
    max_tokens      INT          NOT NULL DEFAULT 4096,
    max_context_window INT,                          -- 上下文窗口大小
    input_price_per_1k DECIMAL(10,6),                -- 输入价格 $/1K tokens
    output_price_per_1k DECIMAL(10,6),               -- 输出价格 $/1K tokens
    rate_limit_rpm  INT,                             -- 模型级限速
    rate_limit_tpm  INT,
    default_params  JSONB        NOT NULL DEFAULT '{}',
                                                     -- 默认推理参数
    capabilities    JSONB        NOT NULL DEFAULT '[]',
                                                     -- 模型能力列表
    max_cost_per_call DECIMAL(10,4),                 -- 单次调用费用上限
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now(),

    UNIQUE (provider_id, model_name)
);

-- 索引
CREATE INDEX idx_mc_provider ON model_configs(provider_id);
CREATE INDEX idx_mc_status   ON model_configs(status);
CREATE INDEX idx_mc_type     ON model_configs(model_type);
```

### default_params JSONB Schema

```json
{
  "temperature": 0.7,
  "top_p": 0.9,
  "frequency_penalty": 0,
  "presence_penalty": 0
}
```

### capabilities JSONB Schema

```json
["text_generation", "function_calling", "json_mode", "vision", "streaming"]
```

---

## 3. model_routing_rules — 路由规则

```sql
CREATE TABLE model_routing_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type       VARCHAR(50)  NOT NULL,            -- 任务类型
    primary_model_id UUID        NOT NULL,            -- ref: model_configs.id（主模型）
    fallback_model_id UUID,                          -- ref: model_configs.id（降级模型）
    priority        INT          NOT NULL DEFAULT 0, -- 优先级（数字越小越优先）
    conditions      JSONB        NOT NULL DEFAULT '{}',
                                                     -- 匹配条件
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_mrr_task_type ON model_routing_rules(task_type, priority);
CREATE INDEX idx_mrr_active    ON model_routing_rules(is_active)
    WHERE is_active = true;
```

### task_type 枚举

| 值 | 说明 |
|------|------|
| `textbook_parse` | 教材解析 |
| `knowledge_extract` | 知识点提取 |
| `game_generate` | 游戏生成 |
| `video_script_generate` | 视频脚本生成 |
| `practice_generate` | 练习题生成 |
| `quality_review` | 质量审核 |
| `report_generate` | 报告生成 |
| `embedding` | 向量生成 |
| `chat` | 对话（AI 辅导）|

### conditions JSONB Schema

```json
{
  "min_context_tokens": 8000,
  "max_input_tokens": 32000,
  "subjects": ["math", "physics"],
  "difficulty": ["advanced"],
  "time_range": {
    "start": "08:00",
    "end": "22:00"
  }
}
```

### 路由匹配逻辑

1. 按 `task_type` 过滤
2. 检查 `conditions` 是否满足（空 conditions = 通配）
3. 按 `priority` 升序取第一条 `is_active = true` 的规则
4. 检查 primary_model 状态和熔断状态
5. 如果主模型不可用，使用 fallback_model

---

## 4. llm_call_logs — 调用日志

```sql
CREATE TABLE llm_call_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        VARCHAR(64)  NOT NULL,           -- 链路追踪 ID
    span_id         VARCHAR(32),                     -- Span ID
    task_type       VARCHAR(50)  NOT NULL,
    model_name      VARCHAR(100) NOT NULL,           -- 实际使用的模型
    provider_name   VARCHAR(50)  NOT NULL,
    caller_service  VARCHAR(100) NOT NULL,            -- 调用方服务名
    user_id         UUID,                            -- ref: users.id（可选）
    status          VARCHAR(20)  NOT NULL,            -- success / failed / timeout / fallback
    input_tokens    INT,
    output_tokens   INT,
    total_tokens    INT,
    input_cost      DECIMAL(10,6),                   -- 输入费用
    output_cost     DECIMAL(10,6),                   -- 输出费用
    total_cost      DECIMAL(10,6),                   -- 总费用
    latency_ms      INT,                             -- 响应耗时（毫秒）
    input_messages  JSONB,                           -- 输入消息（脱敏后存储）
    output_content  TEXT,                            -- 输出内容
    error_message   TEXT,                            -- 错误信息
    request_params  JSONB        NOT NULL DEFAULT '{}',
                                                     -- 请求参数快照
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_lcl_trace     ON llm_call_logs(trace_id);
CREATE INDEX idx_lcl_task_type ON llm_call_logs(task_type, created_at DESC);
CREATE INDEX idx_lcl_model     ON llm_call_logs(model_name, created_at DESC);
CREATE INDEX idx_lcl_user      ON llm_call_logs(user_id)
    WHERE user_id IS NOT NULL;
CREATE INDEX idx_lcl_status    ON llm_call_logs(status);
CREATE INDEX idx_lcl_created   ON llm_call_logs(created_at DESC);
CREATE INDEX idx_lcl_caller    ON llm_call_logs(caller_service);
```

### 分区策略

```sql
-- 按 created_at 月度范围分区
CREATE TABLE llm_call_logs (
    ...
) PARTITION BY RANGE (created_at);

-- 示例分区
CREATE TABLE llm_call_logs_2024_03 PARTITION OF llm_call_logs
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
```

- 热数据保留 6 个月
- 冷数据归档到对象存储（MinIO/S3）
- 通过定时任务每月初创建下月分区 + 归档过期分区

### 安全要求

- `input_messages` 必须脱敏后存储（手机号、API Key 等）
- 脱敏规则参见 [平台支撑 - 日志脱敏](../platform-support.md)

---

## 5. llm_usage_daily — 每日用量统计

```sql
CREATE TABLE llm_usage_daily (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date       DATE         NOT NULL,
    provider_name   VARCHAR(50)  NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    task_type       VARCHAR(50)  NOT NULL,
    call_count      INT          NOT NULL DEFAULT 0,
    success_count   INT          NOT NULL DEFAULT 0,
    failed_count    INT          NOT NULL DEFAULT 0,
    timeout_count   INT          NOT NULL DEFAULT 0,
    fallback_count  INT          NOT NULL DEFAULT 0,
    total_input_tokens  BIGINT   NOT NULL DEFAULT 0,
    total_output_tokens BIGINT   NOT NULL DEFAULT 0,
    total_cost      DECIMAL(12,6) NOT NULL DEFAULT 0,
    avg_latency_ms  INT,
    p95_latency_ms  INT,
    p99_latency_ms  INT,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now(),

    UNIQUE (stat_date, provider_name, model_name, task_type)
);

-- 索引
CREATE INDEX idx_lud_date     ON llm_usage_daily(stat_date);
CREATE INDEX idx_lud_provider ON llm_usage_daily(provider_name);
CREATE INDEX idx_lud_model    ON llm_usage_daily(model_name);
```

---

## 熔断策略

```
+---------------------------+-------------------+
| 触发条件                   | 动作               |
+---------------------------+-------------------+
| 5分钟内 3 次失败            | 该模型熔断 10 分钟   |
| 单次费用 > max_cost_per_call | 拒绝并告警         |
| 延迟 > 超时阈值 * 2        | 计入失败，触发降级   |
+---------------------------+-------------------+
```

熔断状态存储在 Redis 中（`circuit_breaker:{model_name}`），不持久化到数据库。

---

## 关系图

```
model_providers
└── model_configs (provider_id)
    ├── model_routing_rules (primary_model_id, fallback_model_id)
    └── llm_call_logs (model_name, provider_name)
            ↓ 聚合
        llm_usage_daily (provider_name, model_name, task_type)
```

## 常用查询

### 模型调用成功率

```sql
SELECT model_name,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE status = 'success') AS success,
       ROUND(COUNT(*) FILTER (WHERE status = 'success')::numeric / COUNT(*) * 100, 2) AS success_pct
FROM llm_call_logs
WHERE created_at >= now() - interval '24 hours'
GROUP BY model_name
ORDER BY total DESC;
```

### 每日费用趋势

```sql
SELECT stat_date, provider_name, model_name,
       total_cost, call_count, avg_latency_ms
FROM llm_usage_daily
WHERE stat_date >= CURRENT_DATE - 30
ORDER BY stat_date DESC, total_cost DESC;
```

### 费用预警查询

```sql
SELECT provider_name, model_name,
       SUM(total_cost) AS month_cost
FROM llm_usage_daily
WHERE stat_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY provider_name, model_name
HAVING SUM(total_cost) > :alert_threshold
ORDER BY month_cost DESC;
```
