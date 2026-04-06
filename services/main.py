"""
知趣课堂 — FastAPI 应用入口
═══════════════════════════
MVP 单进程部署：所有模块在同一进程内运行。
启动：uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from shared.exceptions import register_exception_handlers
from shared.logging import RequestLoggingMiddleware, configure_logging

settings = get_settings()
logger = structlog.get_logger()


# ── 生命周期 ──────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动 / 关闭钩子"""
    from pathlib import Path
    log_dir = str(Path(__file__).resolve().parent.parent / "logs" / "backend")
    configure_logging(debug=settings.debug, log_dir=log_dir)

    # ── 初始化 Redis ──
    from redis.asyncio import Redis as AsyncRedis
    redis = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis

    # ── 初始化 MinIO ──
    from infrastructure.external.minio_client import init_minio
    init_minio(settings)

    # ── 初始化 LLM Client ──
    from infrastructure.external.llm_client import init_llm_client
    init_llm_client(settings)

    logger.info(
        "app_startup",
        version=settings.app_version,
        debug=settings.debug,
    )
    yield

    # ── 清理 Redis 连接 ──
    await redis.aclose()
    logger.info("app_shutdown")


# ── 创建 FastAPI 实例 ─────────────────────────────────


app = FastAPI(
    title="知趣课堂 API",
    description="K12 AI 课后辅导平台 — MVP",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# ── 中间件（顺序：CORS → 请求日志）─────────────────


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)


# ── 异常处理器 ────────────────────────────────────────

register_exception_handlers(app)


# ── 路由注册 ──────────────────────────────────────────

from interfaces.api import register_routers  # noqa: E402
register_routers(app)


# ── 健康检查 ──────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check():
    """健康检查端点（负载均衡 / k8s readiness probe）"""
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "status": "healthy",
            "version": settings.app_version,
        },
    }


@app.get("/", tags=["system"])
async def root():
    """根路径 — 基本信息"""
    return {
        "name": "知趣课堂 API",
        "version": settings.app_version,
        "docs": "/docs",
    }
