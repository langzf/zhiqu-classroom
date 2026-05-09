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

import json
import queue
import re
import threading
import time
import traceback
import urllib.error
import urllib.request
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

def configure_logging(*, debug: bool = False, log_dir: str | None = None) -> None:
    """
    初始化 structlog。应用启动时调用一次。

    Args:
        debug: True → DEBUG 级别 + ConsoleRenderer（开发友好）
               False → INFO 级别 + JSONRenderer（生产 / 采集）
        log_dir: 日志文件目录。设置后同时输出到文件（JSON 格式，按日期轮转）。
    """
    import logging
    import logging.handlers
    from pathlib import Path

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

    # ── 文件日志（JSON，按日期轮转，保留 30 天）──
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 文件 handler 去除 ANSI 颜色转义码
        import re
        _ansi_re = re.compile(r"\x1b\[[0-9;]*m")

        class _StripAnsiFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                msg = super().format(record)
                return _ansi_re.sub("", msg)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path / "backend.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        file_handler.setFormatter(_StripAnsiFormatter("%(message)s"))

        # root logger 加 file handler（所有 structlog + stdlib 日志都会 propagate 到这里）
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # root logger 也需要 console handler（structlog stdlib factory 不会自动打印到终端）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(console_handler)

    # 使用 stdlib logger factory 让 structlog 的输出同时走 stdlib（→ 文件 + 终端）
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory()
        if log_dir
        else structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ────────────────────────────────────────────────────
# 4. HTTP 请求日志中间件
# ────────────────────────────────────────────────────

# 不记录日志的路径（健康检查等）
_SKIP_PATHS = frozenset({"/health", "/", "/favicon.ico"})

_access_logger = structlog.get_logger("http.access")


class TraceLogReporter:
    """后台批量上报到 trace-log-platform；失败静默，避免影响业务请求。"""

    def __init__(
        self,
        *,
        platform_url: str,
        project_key: str,
        service_name: str,
        enabled: bool = True,
        batch_size: int = 20,
        flush_interval: float = 1.0,
        queue_size: int = 2000,
        timeout: float = 2.0,
    ) -> None:
        self.platform_url = platform_url.rstrip("/")
        self.project_key = project_key
        self.service_name = service_name
        self.enabled = bool(enabled and self.platform_url and self.service_name)
        self.batch_size = max(1, batch_size)
        self.flush_interval = max(0.2, flush_interval)
        self.timeout = max(0.1, timeout)
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=max(100, queue_size))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        if self.enabled:
            self._thread = threading.Thread(target=self._run, name="trace-log-reporter", daemon=True)
            self._thread.start()

    def report(
        self,
        *,
        level: str,
        message: str,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None = None,
        path: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        error: BaseException | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return

        payload = {
            "level": level,
            "message": message,
            "traceId": trace_id,
            "spanId": span_id,
            "parentSpanId": parent_span_id,
            "service": self.service_name,
            "source": "backend",
            "path": path,
            "method": method,
            "statusCode": status_code,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": self._error_payload(error),
            "meta": {
                "projectKey": self.project_key,
                **(meta or {}),
            },
        }
        self._enqueue(payload)

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._flush()

    def _enqueue(self, payload: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(payload)
            except queue.Empty:
                pass

    def _run(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.flush_interval)
            self._flush()

    def _flush(self) -> None:
        logs: list[dict[str, Any]] = []
        for _ in range(self.batch_size):
            try:
                logs.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if not logs:
            return

        body = json.dumps({"source": "backend", "logs": logs}).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.platform_url}/v1/logs/batch",
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "accept": "application/json",
                "user-agent": "zhiqu-classroom-trace/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status >= 300:
                    raise RuntimeError(f"trace upload failed: HTTP {response.status}")
        except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError, RuntimeError):
            return

    @staticmethod
    def _error_payload(error: BaseException | None) -> dict[str, str] | None:
        if error is None:
            return None
        return {
            "name": error.__class__.__name__,
            "message": str(error),
            "module": error.__class__.__module__,
            "stack": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        }


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

    def __init__(
        self,
        app: Any,
        *,
        trace_platform_url: str = "",
        trace_project_key: str = "zhiqu-classroom",
        trace_service_name: str = "zhiqu-backend",
        trace_enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.trace_reporter = TraceLogReporter(
            platform_url=trace_platform_url,
            project_key=trace_project_key,
            service_name=trace_service_name,
            enabled=trace_enabled,
        )

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
        self.trace_reporter.report(
            level="info",
            message="request_start",
            trace_id=trace_id,
            span_id=span_id,
            path=path,
            method=request.method,
            meta={
                "clientIp": client_ip,
            },
        )

        # ── 执行请求 ──
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            self.trace_reporter.report(
                level="error",
                message="request_error",
                trace_id=trace_id,
                span_id=span_id,
                path=path,
                method=request.method,
                status_code=500,
                error=exc,
                meta={"durationMs": duration_ms},
            )
            raise

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
        self.trace_reporter.report(
            level="error" if response.status_code >= 500 else "warn" if response.status_code >= 400 else "info",
            message="request_end",
            trace_id=trace_id,
            span_id=span_id,
            path=path,
            method=request.method,
            status_code=response.status_code,
            meta={"durationMs": duration_ms},
        )

        return response
