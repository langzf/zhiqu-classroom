# 异步任务与重试策略

> 父文档：[README.md](./README.md)

---

## 1. 概述

教育平台有大量耗时操作（教材解析、LLM 调用、视频生成、报告生成等），需要可靠的异步任务机制。MVP 阶段基于 Redis Streams 实现轻量级任务队列，后续可迁移至 RabbitMQ / Celery。

```
生产者（API Handler）
       │  XADD
       ▼
  Redis Stream（持久化队列）
       │  XREADGROUP
       ▼
  消费者（Worker 进程）
       │
       ├── 成功 → XACK
       ├── 失败（可重试）→ 延迟重新入队
       └── 失败（不可重试）→ 死信队列
```

## 2. 任务类型

| 队列名 | 任务类型 | 优先级 | 超时 | 说明 |
|--------|----------|--------|------|------|
| `task:textbook_parse` | 教材解析 | 高 | 300s | 上传 → OCR → 知识点抽取 |
| `task:llm_generate` | LLM 内容生成 | 中 | 120s | 游戏题目/练习题/脚本生成 |
| `task:video_generate` | 视频生成 | 低 | 600s | 调用媒体服务生成视频 |
| `task:report_generate` | 报告生成 | 低 | 180s | 学习报告聚合生成 |
| `task:notification` | 通知发送 | 高 | 30s | 飞书/短信/推送通知 |
| `task:data_aggregate` | 数据聚合 | 低 | 300s | 用量统计、学习数据汇总 |

## 3. 任务消息格式

```json
{
  "task_id": "uuid-v7",
  "task_type": "textbook_parse",
  "payload": {
    "textbook_id": "uuid",
    "file_url": "minio://textbooks/xxx.pdf",
    "options": {"ocr_enabled": true}
  },
  "metadata": {
    "trace_id": "request-trace-id",
    "user_id": "operator-uuid",
    "created_at": "2026-03-25T14:00:00+08:00",
    "priority": "high",
    "max_retries": 3,
    "retry_count": 0,
    "timeout_seconds": 300
  }
}
```

## 4. 任务状态

```
pending → processing → completed
                 │
                 ├── failed → retry_pending → processing（重试）
                 │
                 └── failed → dead_letter（超过最大重试次数）
```

### 状态追踪表

表 `async_tasks`：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | task_id |
| task_type | VARCHAR(50) | NOT NULL | |
| status | VARCHAR(20) | NOT NULL | pending/processing/completed/failed/dead_letter |
| payload | JSONB | NOT NULL | 任务参数 |
| result | JSONB | NULL | 执行结果 |
| error_message | TEXT | NULL | 最后一次错误信息 |
| retry_count | INT | NOT NULL, DEFAULT 0 | 已重试次数 |
| max_retries | INT | NOT NULL, DEFAULT 3 | 最大重试次数 |
| next_retry_at | TIMESTAMP | NULL | 下次重试时间 |
| started_at | TIMESTAMP | NULL | 开始执行时间 |
| completed_at | TIMESTAMP | NULL | 完成时间 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

### 索引

| 索引名 | 字段 | 说明 |
|--------|------|------|
| `idx_async_tasks_status` | status | 按状态查询 |
| `idx_async_tasks_type` | task_type | 按类型查询 |
| `idx_async_tasks_retry` | next_retry_at | 定时扫描待重试任务 |
| `idx_async_tasks_created` | created_at | 时间范围查询 |

## 5. 重试策略

### 指数退避

```python
def calculate_retry_delay(retry_count: int, base_delay: float = 5.0) -> float:
    """指数退避 + 随机抖动"""
    delay = base_delay * (2 ** retry_count)
    jitter = random.uniform(0, delay * 0.1)
    return min(delay + jitter, 300)  # 最大 5 分钟
```

| 重试次数 | 延迟（约） |
|----------|-----------|
| 第 1 次 | ~10s |
| 第 2 次 | ~20s |
| 第 3 次 | ~40s |

### 按任务类型配置

| 任务类型 | 最大重试 | 基础延迟 | 可重试错误 |
|----------|----------|----------|-----------|
| textbook_parse | 3 | 10s | 网络超时、LLM 限速 |
| llm_generate | 3 | 5s | 限速、临时不可用 |
| video_generate | 2 | 30s | 上游服务超时 |
| notification | 5 | 3s | 网络错误 |
| data_aggregate | 2 | 60s | 数据库锁超时 |

### 不可重试错误

以下错误直接进入死信队列，不再重试：

- 参数校验失败（ValidationError）
- 资源不存在（404）
- 权限不足（403）
- LLM 内容安全拒绝
- 费用超限拒绝

## 6. 实现

### 生产者

```python
# services/shared/task_queue.py

class TaskProducer:
    """任务生产者"""

    async def enqueue(
        self,
        task_type: str,
        payload: dict,
        priority: str = "normal",
        max_retries: int = 3,
        timeout_seconds: int = 120,
    ) -> str:
        task_id = str(uuid7())
        stream_name = f"task:{task_type}"

        message = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": json.dumps(payload),
            "trace_id": trace_id_var.get(""),
            "user_id": user_id_var.get(""),
            "priority": priority,
            "max_retries": str(max_retries),
            "retry_count": "0",
            "timeout_seconds": str(timeout_seconds),
            "created_at": datetime.now().isoformat(),
        }

        await self.redis.xadd(stream_name, message)

        # 同步写入状态追踪表
        await self._create_task_record(task_id, task_type, payload, max_retries)

        logger.info("任务入队", task_id=task_id, task_type=task_type, priority=priority)
        return task_id
```

### 消费者

```python
class TaskConsumer:
    """任务消费者 — 以 Consumer Group 方式消费"""

    async def start(self, task_type: str, handler: Callable):
        stream = f"task:{task_type}"
        group = f"group:{task_type}"

        # 确保 Consumer Group 存在
        try:
            await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception:
            pass  # 已存在

        consumer_name = f"{os.environ.get('HOSTNAME', 'worker')}:{os.getpid()}"

        while not is_shutting_down():
            messages = await self.redis.xreadgroup(
                group, consumer_name, {stream: ">"}, count=1, block=5000
            )

            for stream_name, entries in messages:
                for msg_id, data in entries:
                    try:
                        await self._process(msg_id, data, handler, stream, group)
                    except Exception as e:
                        await self._handle_failure(msg_id, data, e, stream, group)

    async def _process(self, msg_id, data, handler, stream, group):
        task_id = data["task_id"]
        timeout = int(data.get("timeout_seconds", 120))

        await self._update_status(task_id, "processing")

        try:
            result = await asyncio.wait_for(
                handler(json.loads(data["payload"])),
                timeout=timeout,
            )
            await self._update_status(task_id, "completed", result=result)
            await self.redis.xack(stream, group, msg_id)
            logger.info("任务完成", task_id=task_id)

        except asyncio.TimeoutError:
            raise RetryableError(f"任务超时 ({timeout}s)")

    async def _handle_failure(self, msg_id, data, error, stream, group):
        task_id = data["task_id"]
        retry_count = int(data.get("retry_count", 0))
        max_retries = int(data.get("max_retries", 3))

        if isinstance(error, NonRetryableError) or retry_count >= max_retries:
            await self._update_status(task_id, "dead_letter", error=str(error))
            await self.redis.xack(stream, group, msg_id)
            logger.error("任务进入死信", task_id=task_id, error=str(error))
        else:
            delay = calculate_retry_delay(retry_count)
            next_retry = datetime.now() + timedelta(seconds=delay)
            await self._update_status(
                task_id, "retry_pending", error=str(error), next_retry_at=next_retry
            )
            await self.redis.xack(stream, group, msg_id)

            # 延迟重新入队（用 sorted set 实现延迟）
            data["retry_count"] = str(retry_count + 1)
            await self.redis.zadd(
                f"retry:{stream}", {json.dumps(data): next_retry.timestamp()}
            )
            logger.warning(
                "任务重试",
                task_id=task_id,
                retry=retry_count + 1,
                delay_s=delay,
            )
```

### 重试调度器

```python
class RetryScheduler:
    """定时扫描 retry sorted set，将到期任务重新入队"""

    async def start(self):
        while not is_shutting_down():
            for stream_key in await self.redis.keys("retry:task:*"):
                stream = stream_key.replace("retry:", "")
                now = datetime.now().timestamp()

                # 取出到期的任务
                tasks = await self.redis.zrangebyscore(stream_key, 0, now, start=0, num=10)
                for task_data in tasks:
                    data = json.loads(task_data)
                    await self.redis.xadd(stream, data)
                    await self.redis.zrem(stream_key, task_data)
                    logger.info("重试任务入队", task_id=data["task_id"])

            await asyncio.sleep(5)
```

## 7. 死信队列处理

死信队列中的任务需要人工介入：

- 管理后台提供死信任务列表
- 支持查看失败原因、任务参数
- 可手动重试（重置 retry_count）或标记忽略
- 超过 30 天的死信任务自动归档

### 管理 API

```
GET    /api/v1/admin/tasks                       🔑  任务列表（支持状态筛选）
GET    /api/v1/admin/tasks/:id                  🔑  任务详情
POST   /api/v1/admin/tasks/:id/retry            🔑  手动重试
POST   /api/v1/admin/tasks/:id/cancel           🔑  取消/忽略
GET    /api/v1/admin/tasks/stats                🔑  队列统计（各状态计数）
```

## 8. 监控指标

| 指标 | 说明 |
|------|------|
| `task_queue_length{queue}` | 各队列当前长度 |
| `task_processing_total{type, status}` | 处理总数（按状态） |
| `task_processing_duration{type}` | 处理耗时分布 |
| `task_retry_total{type}` | 重试总次数 |
| `task_dead_letter_total{type}` | 死信总数 |

告警规则见 [monitoring.md](./monitoring.md)。
