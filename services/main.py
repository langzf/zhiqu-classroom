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
    configure_logging(debug=settings.debug)

    # ── 初始化 Redis ──
    from redis.asyncio import Redis as AsyncRedis
    redis = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    from user_profile.router import set_redis
    set_redis(redis)

    # ── 初始化 MinIO ──
    from shared.minio_client import init_minio
    init_minio(settings)

    # ── 初始化 LLM Client ──
    from shared.llm_client import init_llm_client
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

# 用户认证（公共，无 admin/student 前缀区分）
from user_profile.router import router as user_router          # noqa: E402
app.include_router(user_router)

# Admin 路由 → /api/v1/admin/{service}
from content_engine.router_admin import router as content_admin      # noqa: E402
from ai_tutor.router_admin import router as tutor_admin              # noqa: E402
from learning_orchestrator.router_admin import router as learning_admin  # noqa: E402

app.include_router(content_admin, prefix="/api/v1/admin")
app.include_router(tutor_admin, prefix="/api/v1/admin")
app.include_router(learning_admin, prefix="/api/v1/admin")

# Student 路由 → /api/v1/{service}
from content_engine.router_student import router as content_student      # noqa: E402
from ai_tutor.router_student import router as tutor_student              # noqa: E402
from learning_orchestrator.router_student import router as learning_student  # noqa: E402

app.include_router(content_student, prefix="/api/v1")
app.include_router(tutor_student, prefix="/api/v1")
app.include_router(learning_student, prefix="/api/v1")


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
