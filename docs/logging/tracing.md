# 链路追踪设计

> 父文档：[README.md](./README.md)

---

## 1. 追踪模型

```
            trace_id (全局唯一，整条请求链路共享)
            ┌──────────────────────────────────────┐
            │                                      │
  ┌─────────┴──────────┐   ┌────────────────────┐  │
  │ span_id: aa11      │   │ span_id: bb22      │  │
  │ parent: (none)     │──▶│ parent: aa11       │  │
  │ service: user-     │   │ service: content-  │  │
  │   profile          │   │   engine           │  │
  └────────────────────┘   └────────┬───────────┘  │
                                    │              │
                           ┌────────┴───────────┐  │
                           │ span_id: cc33      │  │
                           │ parent: bb22       │  │
                           │ service: LLM call  │  │
                           └────────────────────┘  │
            └──────────────────────────────────────┘
```

## 2. trace_id 生成与传递

```
1. 客户端发起请求，可携带 X-Request-ID
2. API 网关（Nginx/Traefik）：
   - 如果有 X-Request-ID → 透传
   - 如果没有 → 生成 UUID v4，写入 X-Request-ID
3. FastAPI 中间件：
   - 从 X-Request-ID 读取 → 设为 trace_id
   - 生成 span_id（8 位 hex）
   - 注入 contextvars
4. 服务间调用：
   - HTTP Header 传递 X-Request-ID + X-Span-ID
   - 被调用方读取 → trace_id 复用，parent_span_id 设为上游 span_id
5. 响应头：
   - 返回 X-Trace-ID（方便客户端/前端定位问题）
```

## 3. contextvars 定义

```python
# services/shared/logging/context.py

from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
parent_span_id_var: ContextVar[str] = ContextVar("parent_span_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
```

## 4. span_id 生成

```python
import secrets
import uuid

def generate_span_id() -> str:
    """8 位 hex，足够在单 trace 内唯一"""
    return secrets.token_hex(4)

def generate_trace_id() -> str:
    """UUID v4 格式"""
    return str(uuid.uuid4())
```

## 5. structlog Processor 链

```python
# services/shared/logging/config.py

import structlog
import os
import logging

def setup_logging(json_output: bool = True, log_level: str = "INFO"):
    """初始化 structlog，服务启动时调用一次"""
    processors = [
        structlog.contextvars.merge_contextvars,   # 自动合并 contextvars
        _add_service_context,                       # 注入 service/instance
        _add_trace_context,                         # 注入 trace/span
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        _sanitize_sensitive,                        # 脱敏处理
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def _add_service_context(logger, method_name, event_dict):
    event_dict.setdefault("service", os.environ.get("SERVICE_NAME", "unknown"))
    event_dict.setdefault("instance", os.environ.get("HOSTNAME", "unknown"))
    return event_dict

def _add_trace_context(logger, method_name, event_dict):
    from .context import trace_id_var, span_id_var, parent_span_id_var, user_id_var
    event_dict.setdefault("trace_id", trace_id_var.get(""))
    event_dict.setdefault("span_id", span_id_var.get(""))
    event_dict.setdefault("parent_span_id", parent_span_id_var.get(""))
    event_dict.setdefault("user_id", user_id_var.get(""))
    return event_dict
```

## 6. 上下文注入时机

| 上下文字段 | 注入时机 | 来源 |
|------------|----------|------|
| `service` | 进程启动 | `SERVICE_NAME` 环境变量 |
| `instance` | 进程启动 | `HOSTNAME` 或 `socket.gethostname()` |
| `trace_id` | 请求入口 | `X-Request-ID` Header 或自动生成 |
| `span_id` | 请求入口 | 自动生成 |
| `parent_span_id` | 请求入口 | `X-Span-ID` Header（跨服务调用） |
| `user_id` | JWT 解析后 | Token payload |
| `request_id` | 请求入口 | 等同 trace_id |

## 7. 获取 logger

```python
import structlog

logger = structlog.get_logger("content_engine.textbook_parser")

# 自动附带 service, instance, trace_id, span_id, user_id
logger.info("教材解析完成", textbook_id="xxx", chapters=12, duration_ms=1523)
```
