# 日志格式标准（JSON Schema）

> 父文档：[README.md](./README.md)

---

## 1. 基础字段（所有日志必须包含）

```json
{
  "timestamp": "2026-03-25T14:30:00.123+08:00",
  "level": "INFO",
  "logger": "content_engine.textbook_parser",
  "message": "教材解析完成",
  "service": "content-engine",
  "instance": "content-engine-pod-abc12",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "span_id": "1234abcd",
  "parent_span_id": "",
  "user_id": "",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## 2. 字段说明

| 字段 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
| `timestamp` | string | ✅ | structlog 自动 | ISO 8601 带时区 |
| `level` | string | ✅ | structlog 自动 | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `logger` | string | ✅ | get_logger() 参数 | logger 名称 |
| `message` | string | ✅ | 第一个位置参数 | 事件描述 |
| `service` | string | ✅ | 环境变量 `SERVICE_NAME` | 服务名 |
| `instance` | string | ✅ | `HOSTNAME` / Pod Name | 实例标识 |
| `trace_id` | string | ✅ | X-Request-ID 或自动生成 | 请求链路 ID |
| `span_id` | string | ✅ | 每个服务入口生成 | 当前跨度 ID |
| `parent_span_id` | string | ❌ | 上游传递 | 父跨度 ID |
| `user_id` | string | ❌ | JWT 解析 | 当前用户 |
| `request_id` | string | ✅ | 等同 trace_id | 向后兼容 |

## 3. 扩展字段（按场景附加）

### HTTP 请求日志

```json
{
  "method": "POST",
  "path": "/api/v1/textbooks/parse",
  "query_string": "",
  "client_ip": "10.0.1.100",
  "status_code": 200,
  "duration_ms": 1523,
  "request_size": 2048,
  "response_size": 512,
  "user_agent": "Mozilla/5.0 ..."
}
```

### LLM 调用日志

```json
{
  "llm_provider": "deepseek",
  "llm_model": "deepseek-v3",
  "task_type": "knowledge_extract",
  "input_tokens": 1500,
  "output_tokens": 800,
  "total_tokens": 2300,
  "cost_yuan": 0.0023,
  "llm_latency_ms": 3200,
  "is_fallback": false,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### 异步任务日志

```json
{
  "task_name": "content_engine.textbook_parse",
  "task_id": "celery-uuid-123",
  "task_status": "success",
  "retry_count": 0,
  "queue": "content",
  "execution_ms": 45000,
  "triggered_by": "user-uuid"
}
```

### 审计操作日志

```json
{
  "audit_action": "update",
  "resource_type": "model_config",
  "resource_id": "model-uuid-456",
  "operator_id": "admin-uuid",
  "operator_name": "张老师",
  "ip_address": "10.0.1.50",
  "changes": {
    "before": { "temperature": 0.7 },
    "after": { "temperature": 0.3 }
  }
}
```

## 4. message 字段规范

`message` 是日志的核心可搜索字段：

| 规则 | 说明 |
|------|------|
| 使用中文 | 团队一致性 |
| 简短明确 | 动宾结构：「开始解析教材」「LLM 调用失败」 |
| 不含变量值 | 变量放 KV 字段 |
| 可区分位置 | 同一事件入口/出口用不同 message |

```
✅ "开始解析教材"      ← 配合 textbook_id=xxx
✅ "教材解析完成"      ← 配合 chapters=12, duration_ms=1523
✅ "LLM 调用降级"      ← 配合 primary=xxx, fallback=xxx

❌ "开始解析教材 abc-123"  ← 变量拼进了 message
❌ "done"                  ← 含义不明
❌ "处理"                  ← 太笼统
```
