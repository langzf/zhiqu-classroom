# 各场景日志模板

> 父文档：[README.md](./README.md)

---

## 1. HTTP 请求日志

由 `RequestLoggingMiddleware` 自动生成，无需手写。

### 请求入口

```json
{
  "level": "INFO",
  "logger": "http.access",
  "message": "HTTP 请求开始",
  "method": "POST",
  "path": "/api/v1/textbooks/parse",
  "query_string": "",
  "client_ip": "10.0.1.100",
  "user_agent": "Mozilla/5.0 ...",
  "content_length": 2048
}
```

### 请求出口

```json
{
  "level": "INFO",
  "logger": "http.access",
  "message": "HTTP 请求完成",
  "method": "POST",
  "path": "/api/v1/textbooks/parse",
  "status_code": 200,
  "duration_ms": 1523,
  "response_size": 512
}
```

### 中间件代码

```python
# services/shared/logging/middleware.py

import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .context import trace_id_var, span_id_var, user_id_var

logger = structlog.get_logger("http.access")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 注入追踪上下文
        trace_id = request.headers.get("X-Request-ID") or generate_trace_id()
        span_id = generate_span_id()
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)

        start = time.perf_counter()
        logger.info("HTTP 请求开始",
            method=request.method,
            path=request.url.path,
            query_string=str(request.query_params),
            client_ip=request.client.host if request.client else "",
        )

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # 响应头回写 trace_id
        response.headers["X-Trace-ID"] = trace_id

        log_method = logger.warning if response.status_code >= 400 else logger.info
        log_method("HTTP 请求完成",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
```

---

## 2. 数据库操作日志

通过 SQLAlchemy event 自动记录慢查询。

```python
# 慢查询（>100ms）自动告警
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def _before_execute(conn, cursor, stmt, params, context, executemany):
    conn.info["query_start"] = time.perf_counter()

@event.listens_for(Engine, "after_cursor_execute")
def _after_execute(conn, cursor, stmt, params, context, executemany):
    elapsed = (time.perf_counter() - conn.info["query_start"]) * 1000
    if elapsed > 100:  # 慢查询阈值 100ms
        logger.warning("慢查询",
            sql=stmt[:500],  # 截断防日志爆炸
            duration_ms=round(elapsed, 2),
            params_count=len(params) if params else 0,
        )
```

### 日志示例

```json
{
  "level": "WARNING",
  "logger": "system.db_pool",
  "message": "慢查询",
  "sql": "SELECT * FROM tasks WHERE ...",
  "duration_ms": 253.7,
  "params_count": 3
}
```

---

## 3. 外部服务调用日志

所有外部 HTTP 调用（非 LLM）统一通过 wrapper 记录。

```python
async def external_call(service: str, method: str, url: str, **kwargs):
    start = time.perf_counter()
    logger.info("外部服务调用开始",
        external_service=service, method=method, url=url)
    try:
        resp = await http_client.request(method, url, **kwargs)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("外部服务调用完成",
            external_service=service, status_code=resp.status_code,
            duration_ms=duration_ms)
        return resp
    except Exception as e:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error("外部服务调用失败",
            external_service=service, duration_ms=duration_ms,
            exc_info=True)
        raise
```

---

## 4. 认证鉴权日志

| 事件 | 级别 | message |
|------|------|---------|
| 登录成功 | INFO | `用户登录成功` |
| 登录失败 | WARNING | `用户登录失败` |
| Token 过期 | WARNING | `Token 已过期` |
| 权限不足 | WARNING | `权限校验失败` |
| 连续失败锁定 | ERROR | `账户已锁定` |

```python
# 登录成功
logger.info("用户登录成功",
    user_id=user.id, login_method="sms",
    ip=client_ip, device_id=device_id)

# 登录失败
logger.warning("用户登录失败",
    phone="138****5678",  # 已脱敏
    reason="验证码错误", attempt=3,
    ip=client_ip)

# 权限不足
logger.warning("权限校验失败",
    user_id=user.id, required_role="admin",
    actual_role="teacher", path=request.url.path)
```
