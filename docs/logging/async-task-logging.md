# 异步任务日志

> 父文档：[README.md](./README.md)

---

## 1. 任务生命周期日志

每个异步任务在关键节点记录日志：

```
任务入队 → 开始执行 → [进度更新] → 执行完成/失败 → [重试]
```

| 事件 | 级别 | message |
|------|------|---------|
| 入队 | INFO | `异步任务已入队` |
| 开始执行 | INFO | `异步任务开始执行` |
| 进度更新 | DEBUG | `异步任务进度` |
| 执行成功 | INFO | `异步任务执行完成` |
| 执行失败 | ERROR | `异步任务执行失败` |
| 开始重试 | WARNING | `异步任务重试` |
| 最终失败 | ERROR | `异步任务最终失败（已用尽重试）` |
| 超时 | ERROR | `异步任务超时` |

## 2. 日志示例

```python
logger = structlog.get_logger("task.textbook_parse")

# 入队
logger.info("异步任务已入队",
    task_name="textbook_parse",
    task_id="task-uuid-123",
    queue="content",
    textbook_id="tb-uuid",
    triggered_by="user-uuid",
    priority="normal")

# 开始执行
logger.info("异步任务开始执行",
    task_name="textbook_parse",
    task_id="task-uuid-123",
    worker="worker-01",
    retry_count=0)

# 进度更新（DEBUG，不要用 INFO 避免循环日志）
logger.debug("异步任务进度",
    task_id="task-uuid-123",
    progress_pct=45,
    current_step="解析第3章",
    total_steps=8)

# 执行完成
logger.info("异步任务执行完成",
    task_name="textbook_parse",
    task_id="task-uuid-123",
    execution_ms=45000,
    result_summary={"chapters": 8, "knowledge_points": 42})

# 执行失败 + 将重试
logger.error("异步任务执行失败",
    task_name="textbook_parse",
    task_id="task-uuid-123",
    execution_ms=12000,
    retry_count=1,
    max_retries=3,
    next_retry_delay_s=60,
    exc_info=True)

# 最终失败
logger.error("异步任务最终失败（已用尽重试）",
    task_name="textbook_parse",
    task_id="task-uuid-123",
    total_attempts=4,
    total_execution_ms=180000,
    last_error="ConnectionError: ...")
```

## 3. 定时任务日志

```python
logger = structlog.get_logger("task.scheduled")

# 调度器触发
logger.info("定时任务触发",
    task_name="daily_usage_aggregate",
    schedule="0 2 * * *",
    trigger_time="2026-03-25T02:00:00+08:00")

# 完成
logger.info("定时任务完成",
    task_name="daily_usage_aggregate",
    execution_ms=5200,
    records_processed=1250)
```

## 4. 入库说明

关键任务执行记录写入 `task_executions` 表：

| 字段 | 说明 |
|------|------|
| `task_id` | 任务 ID |
| `task_name` | 任务名 |
| `status` | pending / running / success / failed / timeout |
| `retry_count` | 已重试次数 |
| `execution_ms` | 执行耗时 |
| `error_message` | 失败原因 |
| `result_summary` | JSONB，成功时的摘要 |
| `triggered_by` | 触发者（user_id 或 scheduler） |
| `started_at` | 开始时间 |
| `completed_at` | 结束时间 |

普通进度日志只走 Loki，不入库。
