"""
shared.logging — structlog 统一配置 & 请求日志中间件
═══════════════════════════════════════════════════════
设计规范：docs/archive/logging/
MVP 精简：JSON stdout → 终端查看 / Docker json-file → Promtail → Loki

职责：
  1. configure_logging()  — 应用启动时调用一次
  2. contextvars 追踪变量  — trace_id / span_id / user_id
  3. 敏感数据脱敏处理器    — 手机号、token 等自动掩码
  4. RequestLoggingMiddleware — HTTP 请求入口/出口自动日志
"""

from __future__ import annotations

import re
import time
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ────────────────────────────────────────────────────
# 1. 上下文变量（contextvars）— 链路追踪
# ────────────────────────────────────────────────────

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


def generate_trace_id() -> str:
    """生成 trace_id（UUID4 hex，32 字符）"""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """生成 span_id（UUID4 前 16 位）"""
    return uuid.uuid4().hex[:16]


# ────────────────────────────────────────────────────
# 2. structlog 自定义处理器
# ────────────────────────────────────────────────────

# 脱敏正则
_PHONE_RE = re.compile(r"(1[3-9]\d)\d{4}(\d{4})")
_TOKEN_RE = re.compile(r"(eyJ[\w-]+\.[\w-]+)\.[A-Za-z0-9_-]+")

# 需要脱敏的字段名（精确匹配 / 前缀匹配）
_SENSITIVE_KEYS = frozenset({
    "phone", "mobile", "password", "secret",
    "access_token", "refresh_token", "token",
    "authorization", "cookie", "wx_openid",
    "open_id", "union_id", "id_card",
})


def _mask_value(key: str, value: Any) -> Any:
    """对敏感字段值做掩码处理"""
    if not isinstance(value, str) or not value:
        return value

    key_lower = key.lower()

    # 完全掩码：密码、密钥类
    if any(k in key_lower for k in ("password", "secret")):
        return "***"

    # Token 类：保留前缀 + 掩码
    if any(k in key_lower for k in ("token", "authorization", "cookie")):
        if len(value) > 12:
            return value[:8] + "****" + value[-4:]
        return "***"

    # 手机号：138****5678
    if any(k in key_lower for k in ("phone", "mobile")):
        return _PHONE_RE.sub(r"\1****\2", value)

    # openid / union_id：保留前 6 + 后 4
    if any(k in key_lower for k in ("openid", "open_id", "union_id")):
        if len(value) > 12:
            return value[:6] + "****" + value[-4:]
        return "***"

    return value


def sanitize_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog 处理器：自动脱敏敏感字段"""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS or any(
            s in key.lower() for s in ("phone", "mobile", "token", "password", "secret", "openid")
        ):
            event_dict[key] = _mask_value(key, event_dict[key])

    # 对 event 内容也做手机号/JWT 脱敏
    event = event_dict.get("event", "")
    if isinstance(event, str):
        event = _PHONE_RE.sub(r"\1****\2", event)
        event = _TOKEN_RE.sub(r"\1.****", event)
        event_dict["event"] = event

    return event_dict


def inject_context_vars(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog 处理器：注入 trace_id / span_id / user_id"""
    ctx_trace = trace_id_var.get("")
    ctx_span = span_id_var.get("")
    ctx_user = user_id_var.get("")
    if ctx_trace:
        event_dict.setdefault("trace_id", ctx_trace)
    if ctx_span:
        event_dict.setdefault("span_id", ctx_span)
    if ctx_user:
        event_dict.setdefault("user_id", ctx_user)
    return event_dict


# ────────────────────────────────────────────────────
# 3. structlog 配置
# ────────────────────────────────────────────────────

def configure_logging(*, debug: bool = False) -> None:
    """
    初始化 structlog。应用启动时调用一次。

    Args:
        debug: True → DEBUG 级别 + ConsoleRenderer（开发友好）
               False → INFO 级别 + JSONRenderer（生产 / 采集）
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        inject_context_vars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        sanitize_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        # 开发模式：彩色终端输出
        shared_processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )
        min_level = 10  # DEBUG
    else:
        # 生产模式：JSON 输出 → stdout → Promtail → Loki
        shared_processors.append(structlog.processors.JSONRenderer())
        min_level = 20  # INFO

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ────────────────────────────────────────────────────
# 4. HTTP 请求日志中间件
# ────────────────────────────────────────────────────

# 不记录日志的路径（健康检查等）
_SKIP_PATHS = frozenset({"/health", "/", "/favicon.ico"})

_access_logger = structlog.get_logger("http.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求日志中间件

    每请求自动：
    - 生成 / 透传 trace_id + span_id
    - 绑定 contextvars（后续业务日志自动携带）
    - 入口 INFO: method, path, client_ip
    - 出口 INFO: status_code, duration_ms
    - 响应头回写 X-Trace-ID
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 健康检查等跳过日志
        if path in _SKIP_PATHS:
            return await call_next(request)

        # ── 追踪上下文 ──
        trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
        span_id = generate_span_id()
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)
        user_id_var.set("")  # 重置，认证后由 deps 设置

        # ── 绑定 structlog contextvars ──
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            span_id=span_id,
        )

        # ── 请求入口日志 ──
        client_ip = request.client.host if request.client else ""
        _access_logger.info(
            "request_in",
            method=request.method,
            path=path,
            query_string=str(request.query_params) or "",
            client_ip=client_ip,
        )

        # ── 执行请求 ──
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # ── 响应头回写 ──
        response.headers["X-Trace-ID"] = trace_id

        # ── 请求出口日志 ──
        log_fn = (
            _access_logger.warning
            if response.status_code >= 400
            else _access_logger.info
        )
        log_fn(
            "request_out",
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
