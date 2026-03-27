# 异步任务管理

> Schema: `platform`
> 最后更新: 2026-03-25

---

## 概述

异步任务管理负责追踪所有后台异步任务的生命周期，包括教材解析、互动内容生成、报告生成、数据导出等。
提供任务状态查询、重试机制和超时管理能力。

与 Redis Streams 事件驱动的关系：
- **Redis Streams**：负责事件发布/消费的实时消息传递
- **async_tasks 表**：负责任务状态持久化、历史查询、重试管理

---

## 1. async_tasks（异步任务主表）

### DDL

```sql
CREATE TABLE platform.async_tasks (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type       VARCHAR(50)     NOT NULL,
    task_name       VARCHAR(200)    NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',
    priority        INT             NOT NULL DEFAULT 0,
    resource_type   VARCHAR(50)     NULL,
    resource_id     UUID            NULL,
    input_payload   JSONB           NULL,
    output_payload  JSONB           NULL,
    error_message   TEXT            NULL,
    retry_count     INT             NOT NULL DEFAULT 0,
    max_retries     INT             NOT NULL DEFAULT 3,
    scheduled_at    TIMESTAMP       NULL,
    started_at      TIMESTAMP       NULL,
    completed_at    TIMESTAMP       NULL,
    timeout_seconds INT             NOT NULL DEFAULT 300,
    worker_id       VARCHAR(100)    NULL,
    created_by      UUID            NULL,           -- ref: users.id
    created_at      TIMESTAMP       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT now()
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 任务 ID |
| task_type | VARCHAR(50) | NOT NULL | 任务类型：`textbook_parse` / `resource_generate` / `report_generate` / `data_export` / `embedding_sync` / `notification_batch` |
| task_name | VARCHAR(200) | NOT NULL | 人类可读名称，如「解析教材《小学数学三年级上》」 |
| status | VARCHAR(20) | NOT NULL | 任务状态（见状态机） |
| priority | INT | NOT NULL | 优先级：0=普通, 1=高, 2=紧急 |
| resource_type | VARCHAR(50) | NULL | 关联资源类型 |
| resource_id | UUID | NULL | 关联资源 ID |
| input_payload | JSONB | NULL | 任务输入参数 |
| output_payload | JSONB | NULL | 任务输出结果摘要 |
| error_message | TEXT | NULL | 最后一次失败的错误信息 |
| retry_count | INT | NOT NULL | 已重试次数 |
| max_retries | INT | NOT NULL | 最大重试次数 |
| scheduled_at | TIMESTAMP | NULL | 计划执行时间（为 NULL 表示立即执行） |
| started_at | TIMESTAMP | NULL | 实际开始时间 |
| completed_at | TIMESTAMP | NULL | 完成时间（成功或最终失败） |
| timeout_seconds | INT | NOT NULL | 超时阈值（秒） |
| worker_id | VARCHAR(100) | NULL | 执行的 Worker 标识 |
| created_by | UUID | NULL | 创建者 — ref: users.id（系统任务为 NULL） |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

### 索引

```sql
-- 按状态查任务（Worker 拉取待执行任务）
CREATE INDEX idx_async_tasks_status
    ON platform.async_tasks (status, priority DESC, created_at);

-- 按任务类型 + 状态
CREATE INDEX idx_async_tasks_type_status
    ON platform.async_tasks (task_type, status, created_at DESC);

-- 按关联资源查（如查某教材的解析任务）
CREATE INDEX idx_async_tasks_resource
    ON platform.async_tasks (resource_type, resource_id)
    WHERE resource_id IS NOT NULL;

-- 超时检测（查找已开始但超时的任务）
CREATE INDEX idx_async_tasks_timeout
    ON platform.async_tasks (started_at, timeout_seconds)
    WHERE status = 'running';

-- 按创建者查
CREATE INDEX idx_async_tasks_created_by
    ON platform.async_tasks (created_by, created_at DESC)
    WHERE created_by IS NOT NULL;
```

### 状态机

```
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │ (retry_count < max_retries)
┌─────────┐   ┌─────────┐   ┌───────────┐   ┌───────┴──┐
│ pending  │──►│ running │──►│ completed │   │  failed  │
└─────────┘   └────┬────┘   └───────────┘   └──────────┘
     │              │                             ▲
     │              └─────────────────────────────┘
     │                    (error/timeout)
     ▼
┌───────────┐
│ cancelled │
└───────────┘
```

| 状态 | 说明 |
|------|------|
| `pending` | 等待执行 |
| `running` | 执行中（Worker 已认领） |
| `completed` | 成功完成 |
| `failed` | 最终失败（重试耗尽或不可重试错误） |
| `cancelled` | 手动取消 |

### input_payload 示例

```json
// textbook_parse
{
  "textbook_id": "550e8400-...",
  "file_url": "textbooks/2026/math-grade3.pdf",
  "options": {
    "extract_knowledge_points": true,
    "generate_embeddings": true
  }
}

// resource_generate
{
  "knowledge_point_id": "660e8400-...",
  "resource_types": ["game_quiz", "practice_set"],
  "difficulty": "basic"
}
```

---

## 2. async_task_logs（任务执行日志）

记录每次任务执行尝试的详细信息（包括重试），用于排查和分析。

### DDL

```sql
CREATE TABLE platform.async_task_logs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID            NOT NULL,       -- ref: async_tasks.id
    attempt         INT             NOT NULL,
    status          VARCHAR(20)     NOT NULL,
    worker_id       VARCHAR(100)    NULL,
    started_at      TIMESTAMP       NOT NULL,
    ended_at        TIMESTAMP       NULL,
    duration_ms     INT             NULL,
    error_message   TEXT            NULL,
    error_stack     TEXT            NULL,
    output_summary  JSONB           NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT now()
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 日志 ID |
| task_id | UUID | NOT NULL | 关联 async_tasks.id |
| attempt | INT | NOT NULL | 第几次尝试（从 1 开始） |
| status | VARCHAR(20) | NOT NULL | 本次执行结果：`success` / `error` / `timeout` |
| worker_id | VARCHAR(100) | NULL | 执行 Worker |
| started_at | TIMESTAMP | NOT NULL | 本次开始时间 |
| ended_at | TIMESTAMP | NULL | 本次结束时间 |
| duration_ms | INT | NULL | 执行耗时(毫秒) |
| error_message | TEXT | NULL | 错误信息 |
| error_stack | TEXT | NULL | 错误堆栈（仅开发/staging 环境记录） |
| output_summary | JSONB | NULL | 执行结果摘要 |
| created_at | TIMESTAMP | NOT NULL | |

### 索引

```sql
-- 按任务查所有执行记录
CREATE INDEX idx_task_logs_task_id
    ON platform.async_task_logs (task_id, attempt);

-- 按状态统计（故障率分析）
CREATE INDEX idx_task_logs_status
    ON platform.async_task_logs (status, created_at DESC);
```

---

## 枚举值

| 枚举名 | 值 | 使用字段 |
|--------|-----|----------|
| task_type | `textbook_parse`, `resource_generate`, `report_generate`, `data_export`, `embedding_sync`, `notification_batch` | async_tasks.task_type |
| task_status | `pending`, `running`, `completed`, `failed`, `cancelled` | async_tasks.status |
| task_log_status | `success`, `error`, `timeout` | async_task_logs.status |
| priority | `0`=普通, `1`=高, `2`=紧急 | async_tasks.priority |

---

## 与 Redis Streams 的协作

```
用户上传教材
    │
    ▼
async_tasks INSERT (status=pending)
    │
    ▼
Redis Stream: stream:textbook.uploaded
    │
    ▼
Worker 消费事件
    ├── UPDATE async_tasks SET status=running
    ├── INSERT async_task_logs (attempt=1)
    │
    ├── 成功 → UPDATE status=completed
    │         INSERT task_log (status=success)
    │         Redis Stream: stream:textbook.parsed
    │
    └── 失败 → INSERT task_log (status=error)
              if retry_count < max_retries:
                  UPDATE status=pending, retry_count++
                  重新入队
              else:
                  UPDATE status=failed
```

---

## 使用场景

### 查看某教材的解析任务进度

```sql
SELECT t.status, t.retry_count, t.started_at, t.completed_at,
       t.error_message, t.output_payload
FROM platform.async_tasks t
WHERE t.resource_type = 'textbook'
  AND t.resource_id = '550e8400-...'
ORDER BY t.created_at DESC
LIMIT 1;
```

### 超时任务检测（定时任务执行）

```sql
UPDATE platform.async_tasks
SET status = 'failed',
    error_message = 'Task timeout',
    updated_at = now()
WHERE status = 'running'
  AND started_at + (timeout_seconds * INTERVAL '1 second') < now();
```

### 任务成功率统计

```sql
SELECT task_type,
       COUNT(*) FILTER (WHERE status = 'completed') AS success_count,
       COUNT(*) FILTER (WHERE status = 'failed') AS fail_count,
       ROUND(
           COUNT(*) FILTER (WHERE status = 'completed')::decimal /
           NULLIF(COUNT(*), 0) * 100, 1
       ) AS success_rate
FROM platform.async_tasks
WHERE created_at > now() - INTERVAL '7 days'
GROUP BY task_type;
```
