# LLM 调用历史与用量统计

> 父文档：[README.md](./README.md)

---

## 1. 概述

记录每次 LLM 调用的完整信息（输入/输出/耗时/费用），按日聚合统计用量，提供费用预警能力。

```
LLMClient.complete()
       │
       ▼
  llm_call_logs（每次调用明细）
       │  定时聚合
       ▼
  llm_usage_daily（每日汇总）
       │
       ▼
  管理后台看板 + 费用预警
```

## 2. 调用日志

### 数据模型

表 `llm_call_logs`：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| trace_id | VARCHAR(64) | NOT NULL | 请求链路 ID |
| task_type | VARCHAR(50) | NOT NULL | 业务任务类型 |
| model_config_id | UUID | NOT NULL | 使用的模型配置 |
| provider_name | VARCHAR(50) | NOT NULL | 冗余：供应商名称 |
| model_name | VARCHAR(100) | NOT NULL | 冗余：模型名称 |
| caller_service | VARCHAR(50) | NOT NULL | 调用方服务名 |
| user_id | UUID | NULL | 触发调用的用户（如有） |
| input_messages | JSONB | NOT NULL | 输入 messages（脱敏后） |
| input_tokens | INT | NOT NULL | 输入 token 数 |
| output_content | TEXT | NOT NULL | 输出内容 |
| output_tokens | INT | NOT NULL | 输出 token 数 |
| total_tokens | INT | NOT NULL | 总 token 数 |
| cost_yuan | DECIMAL(10,6) | NOT NULL | 本次调用费用（元） |
| latency_ms | INT | NOT NULL | 响应延迟（毫秒） |
| status | VARCHAR(20) | NOT NULL | `success` / `failed` / `timeout` / `fallback` |
| error_message | TEXT | NULL | 失败时的错误信息 |
| params_used | JSONB | NOT NULL | 实际使用的调用参数 |
| is_fallback | BOOLEAN | NOT NULL, DEFAULT false | 是否使用了降级模型 |
| metadata | JSONB | DEFAULT '{}' | 扩展信息（关联的 resource_id 等） |
| created_at | TIMESTAMP | NOT NULL | |

### 索引

| 索引名 | 字段 | 说明 |
|--------|------|------|
| `idx_lcl_trace` | trace_id | 按链路查询 |
| `idx_lcl_task_type` | task_type | 按任务类型统计 |
| `idx_lcl_model` | model_config_id | 按模型筛选 |
| `idx_lcl_user` | user_id | 按用户查询 |
| `idx_lcl_status` | status | 按状态筛选 |
| `idx_lcl_created` | created_at | 时间范围查询 |
| `idx_lcl_caller` | (caller_service, created_at) | 按服务+时间复合查询 |

### 分区策略

按 `created_at` 月份范围分区：

```sql
CREATE TABLE llm_call_logs (
    ...
) PARTITION BY RANGE (created_at);

-- 每月一个分区
CREATE TABLE llm_call_logs_2026_03
    PARTITION OF llm_call_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
```

- **热数据**：保留最近 6 个月分区（在线查询）
- **冷数据**：超过 6 个月的分区导出为 Parquet → 上传到对象存储（MinIO/OSS）→ 删除分区
- **归档调度**：每月 1 日凌晨执行（Cron 任务）

## 3. 用量统计

### 数据模型

表 `llm_usage_daily`：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| stat_date | DATE | NOT NULL | 统计日期 |
| provider_name | VARCHAR(50) | NOT NULL | |
| model_name | VARCHAR(100) | NOT NULL | |
| task_type | VARCHAR(50) | NOT NULL | |
| total_calls | INT | NOT NULL, DEFAULT 0 | 调用次数 |
| success_calls | INT | NOT NULL, DEFAULT 0 | 成功次数 |
| failed_calls | INT | NOT NULL, DEFAULT 0 | 失败次数 |
| fallback_calls | INT | NOT NULL, DEFAULT 0 | 降级次数 |
| total_input_tokens | BIGINT | NOT NULL, DEFAULT 0 | 总输入 tokens |
| total_output_tokens | BIGINT | NOT NULL, DEFAULT 0 | 总输出 tokens |
| total_cost_yuan | DECIMAL(12,4) | NOT NULL, DEFAULT 0 | 总费用（元） |
| avg_latency_ms | INT | NOT NULL, DEFAULT 0 | 平均延迟 |
| p95_latency_ms | INT | NOT NULL, DEFAULT 0 | P95 延迟 |
| p99_latency_ms | INT | NOT NULL, DEFAULT 0 | P99 延迟 |
| created_at | TIMESTAMP | NOT NULL | |

**唯一约束：** `(stat_date, provider_name, model_name, task_type)`

### 聚合逻辑

每日凌晨定时任务，从 `llm_call_logs` 聚合前一天数据：

```python
async def aggregate_daily_usage(date: date):
    """聚合指定日期的 LLM 用量"""
    sql = """
        INSERT INTO llm_usage_daily
            (id, stat_date, provider_name, model_name, task_type,
             total_calls, success_calls, failed_calls, fallback_calls,
             total_input_tokens, total_output_tokens, total_cost_yuan,
             avg_latency_ms, p95_latency_ms, p99_latency_ms, created_at)
        SELECT
            gen_random_uuid(), :date, provider_name, model_name, task_type,
            COUNT(*),
            COUNT(*) FILTER (WHERE status = 'success'),
            COUNT(*) FILTER (WHERE status = 'failed'),
            COUNT(*) FILTER (WHERE is_fallback = true),
            SUM(input_tokens), SUM(output_tokens), SUM(cost_yuan),
            AVG(latency_ms)::INT,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::INT,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms)::INT,
            NOW()
        FROM llm_call_logs
        WHERE created_at >= :date AND created_at < :date + INTERVAL '1 day'
        GROUP BY provider_name, model_name, task_type
        ON CONFLICT (stat_date, provider_name, model_name, task_type)
        DO UPDATE SET
            total_calls = EXCLUDED.total_calls,
            success_calls = EXCLUDED.success_calls,
            failed_calls = EXCLUDED.failed_calls,
            fallback_calls = EXCLUDED.fallback_calls,
            total_input_tokens = EXCLUDED.total_input_tokens,
            total_output_tokens = EXCLUDED.total_output_tokens,
            total_cost_yuan = EXCLUDED.total_cost_yuan,
            avg_latency_ms = EXCLUDED.avg_latency_ms,
            p95_latency_ms = EXCLUDED.p95_latency_ms,
            p99_latency_ms = EXCLUDED.p99_latency_ms;
    """
    await db.execute(text(sql), {"date": date})
```

## 4. 管理后台

### 功能页面

| 页面 | 功能 |
|------|------|
| **调用日志** | 分页查看调用记录，按时间/模型/任务类型/状态筛选，详情查看输入输出 |
| **用量看板** | 日/周/月维度：调用量趋势、费用分布、成功率、延迟分布 |
| **费用预警** | 日/月费用阈值设置，超限告警（通知渠道：钉钉/飞书/邮件） |

### 管理 API

```
GET    /api/v1/admin/llm/call-logs                 🔑  调用日志列表（分页）
GET    /api/v1/admin/llm/call-logs/:id             🔑  调用日志详情

GET    /api/v1/admin/llm/usage/daily               🔑  每日用量统计
GET    /api/v1/admin/llm/usage/summary             🔑  用量汇总看板数据
```

### 调用日志查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| page | INT | 页码（默认 1） |
| page_size | INT | 每页条数（默认 20，最大 100） |
| task_type | STRING | 筛选任务类型 |
| model_name | STRING | 筛选模型 |
| provider_name | STRING | 筛选供应商 |
| status | STRING | 筛选状态 |
| start_time | DATETIME | 起始时间 |
| end_time | DATETIME | 截止时间 |
| trace_id | STRING | 精确匹配链路 ID |
| user_id | UUID | 筛选触发用户 |

### 用量看板聚合维度

```
GET /api/v1/admin/llm/usage/summary?period=week&group_by=model

响应示例：
{
  "code": 0,
  "message": "ok",
  "data": {
    "period": "2026-03-19 ~ 2026-03-25",
    "total_calls": 12580,
    "total_cost_yuan": 234.56,
    "success_rate": 0.987,
    "avg_latency_ms": 1250,
    "breakdown": [
      {
        "model_name": "deepseek-v3",
        "calls": 8920,
        "cost_yuan": 89.20,
        "success_rate": 0.992,
        "avg_latency_ms": 980
      },
      ...
    ]
  }
}
```

## 5. 费用预警

### 阈值配置

通过 `sys_configs` 表（配置中心）管理预警阈值：

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `llm.cost.daily_warn` | 100 | 日费用预警（元） |
| `llm.cost.daily_limit` | 200 | 日费用硬限（元），超过拒绝非关键调用 |
| `llm.cost.monthly_warn` | 2000 | 月费用预警（元） |
| `llm.cost.monthly_limit` | 5000 | 月费用硬限（元），超过自动降级 |

### 预警触发流程

```
每次 LLM 调用完成
       │
       ▼
  累加 Redis 计数器（daily_cost:{date}）
       │
       ├── > daily_warn → 发送通知
       ├── > daily_limit → 拒绝非关键调用 + 告警
       │
       ▼
  每小时聚合月累计
       │
       ├── > monthly_warn → 发送通知
       └── > monthly_limit → 自动降级到低价模型 + 告警
```
