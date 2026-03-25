# 日志轮转与保留策略

> 父文档：[README.md](./README.md)

---

## 1. 分层保留策略

| 日志类型 | Loki（热存储） | PostgreSQL | 对象存储（冷归档） | 总保留 |
|----------|---------------|------------|-------------------|--------|
| HTTP 访问日志 | 30 天 | — | 可选 90 天 | 30~90 天 |
| 业务逻辑日志 | 30 天 | — | 可选 90 天 | 30~90 天 |
| LLM 调用日志 | 30 天 | 6 个月 | 1 年 | 1 年 |
| 异步任务日志 | 30 天 | 6 个月 | — | 6 个月 |
| 审计日志 | 30 天 | 永久 | — | 永久 |
| 系统运维日志 | 14 天 | — | — | 14 天 |

## 2. Docker 日志轮转

```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5",
    "compress": "true"
  }
}
```

单容器最多 5 × 50MB = 250MB，总量可控。

## 3. Loki 自动保留

已在 Loki 配置中设置：

```yaml
limits_config:
  retention_period: 720h  # 30天

compactor:
  retention_enabled: true
  retention_delete_delay: 2h
  compaction_interval: 10m
```

不同日志类型如需不同保留时间，可在 Loki 3.x 中通过 `per_stream_rate_limit` + label 策略实现：

```yaml
# 按 label 差异化保留（Loki 3.x）
overrides:
  # 系统日志保留更短
  system:
    retention_period: 336h  # 14天
```

## 4. PostgreSQL 分区策略

`llm_call_logs` 表按月分区（已在 [数据模型](../data-model/platform-support.md) 中定义）：

```sql
-- 创建主表
CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY,
    -- ... 其他字段 ...
    created_at TIMESTAMP NOT NULL
) PARTITION BY RANGE (created_at);

-- 每月分区
CREATE TABLE llm_call_logs_2026_03
    PARTITION OF llm_call_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE llm_call_logs_2026_04
    PARTITION OF llm_call_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

**分区管理脚本**（每月 cron 自动创建下月分区 + 归档过期分区）：

```python
# scripts/db/manage_partitions.py
import datetime

def create_next_month_partition():
    """提前创建下月分区"""
    next_month = (datetime.date.today().replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    after_month = (next_month + datetime.timedelta(days=32)).replace(day=1)
    sql = f"""
    CREATE TABLE IF NOT EXISTS llm_call_logs_{next_month:%Y_%m}
        PARTITION OF llm_call_logs
        FOR VALUES FROM ('{next_month}') TO ('{after_month}');
    """
    return sql

def archive_old_partitions(months_to_keep: int = 6):
    """归档超过 N 个月的分区"""
    cutoff = (datetime.date.today() - datetime.timedelta(days=months_to_keep * 30)).replace(day=1)
    # 1. pg_dump 导出分区
    # 2. 上传到 MinIO/S3
    # 3. DROP PARTITION
    pass
```

## 5. 冷数据归档流程

```
月度归档 cron（每月1日 03:00 执行）:
  1. 检查 6 个月前的分区是否存在
  2. pg_dump 导出为 CSV + gzip
  3. 上传到 MinIO/S3: s3://zhiqu-archive/llm_call_logs/2025_09.csv.gz
  4. 验证上传成功（MD5 校验）
  5. DROP PARTITION（仅验证通过后）
  6. 记录归档日志到 audit_logs
```

## 6. 存储容量预估

假设日均 10,000 次 LLM 调用：

| 存储 | 每条大小 | 日增量 | 月增量 | 6 个月 |
|------|----------|--------|--------|--------|
| Loki（JSON 日志） | ~1 KB | 10 MB | 300 MB | 1.8 GB |
| PostgreSQL（结构化） | ~2 KB | 20 MB | 600 MB | 3.6 GB |
| 冷归档（gzip CSV） | ~0.5 KB | — | ~150 MB | ~900 MB |

MVP 阶段日调用量远小于此，存储压力不大。
