# 健康检查与优雅停机

> 父文档：[README.md](./README.md)

---

## 1. 概述

每个微服务暴露标准化健康端点，支持容器编排（Docker / K8s）的存活探针和就绪探针，实现零停机部署。

## 2. 健康端点

### 2.1 存活检查（Liveness）

```
GET /health/live → 200 {"status": "ok"}
```

- **用途**：判断进程是否存活，死循环/僵死时自动重启
- **检查内容**：仅返回 200，无外部依赖检查
- **失败处理**：容器编排自动重启

### 2.2 就绪检查（Readiness）

```
GET /health/ready → 200 | 503

200 响应：
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "latency_ms": 3},
    "redis": {"status": "ok", "latency_ms": 1},
    "minio": {"status": "ok", "latency_ms": 8}
  }
}

503 响应：
{
  "status": "degraded",
  "checks": {
    "database": {"status": "ok", "latency_ms": 3},
    "redis": {"status": "fail", "error": "Connection refused"},
    "minio": {"status": "ok", "latency_ms": 8}
  }
}
```

- **用途**：判断服务是否可接收流量
- **检查内容**：数据库连接、Redis 连接、对象存储连通性
- **失败处理**：从负载均衡中摘除，不再分配请求

### 2.3 详细信息（Info）

```
GET /health/info → 200
{
  "service": "content-engine",
  "version": "0.1.0",
  "git_commit": "a1b2c3d",
  "uptime_seconds": 3600,
  "python_version": "3.12.3",
  "start_time": "2026-03-25T08:00:00+08:00"
}
```

- **用途**：运维排查，确认部署版本
- **安全**：生产环境可选禁用或限制内网访问

## 3. 实现

```python
# services/shared/health.py

import time
from fastapi import APIRouter, Response

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.time()


@router.get("/live")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def readiness(response: Response):
    checks = {}

    # 数据库
    try:
        start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "ok",
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
    except Exception as e:
        checks["database"] = {"status": "fail", "error": str(e)}

    # Redis
    try:
        start = time.perf_counter()
        await redis.ping()
        checks["redis"] = {
            "status": "ok",
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
    except Exception as e:
        checks["redis"] = {"status": "fail", "error": str(e)}

    all_ok = all(c["status"] == "ok" for c in checks.values())
    if not all_ok:
        response.status_code = 503

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }


@router.get("/info")
async def info():
    return {
        "service": os.environ.get("SERVICE_NAME", "unknown"),
        "version": os.environ.get("APP_VERSION", "dev"),
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "uptime_seconds": int(time.time() - _start_time),
        "python_version": platform.python_version(),
        "start_time": datetime.fromtimestamp(_start_time).isoformat(),
    }
```

## 4. 优雅停机

### 4.1 流程

```
收到 SIGTERM
    │
    ├── 1. 标记就绪检查返回 503（摘流量）
    ├── 2. 等待 grace_period（默认 10s，让在途请求完成）
    ├── 3. 停止接收新请求
    ├── 4. 等待所有活跃请求完成（最多 30s）
    ├── 5. 关闭数据库连接池
    ├── 6. 关闭 Redis 连接
    └── 7. 退出进程
```

### 4.2 实现

```python
# services/shared/lifecycle.py

import asyncio
import signal

_shutting_down = False


def is_shutting_down() -> bool:
    return _shutting_down


async def graceful_shutdown(app):
    """注册优雅停机处理"""
    global _shutting_down

    async def _shutdown(sig):
        logger.info("收到停机信号", signal=sig.name)
        _shutting_down = True

        # 等待在途请求完成
        logger.info("等待在途请求完成", grace_period_s=10)
        await asyncio.sleep(10)

        # 关闭资源
        logger.info("关闭数据库连接池")
        await close_db()

        logger.info("关闭 Redis 连接")
        await close_redis()

        logger.info("服务已停止")

    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(_shutdown(s))
        )
```

### 4.3 就绪检查联动

```python
@router.get("/ready")
async def readiness(response: Response):
    if is_shutting_down():
        response.status_code = 503
        return {"status": "shutting_down"}
    # ... 正常检查逻辑
```

## 5. Docker / K8s 配置

### Docker Compose

```yaml
services:
  content-engine:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    stop_grace_period: 30s
```

### K8s Deployment（后期）

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 2
```

## 6. 超时与重试参数

| 参数 | 值 | 说明 |
|------|-----|------|
| liveness 间隔 | 30s | |
| liveness 超时 | 5s | |
| liveness 失败阈值 | 3 次 | 连续 3 次失败 → 重启 |
| readiness 间隔 | 10s | |
| readiness 超时 | 5s | |
| readiness 失败阈值 | 2 次 | 连续 2 次失败 → 摘流量 |
| 停机宽限期 | 30s | SIGTERM 后最多等待 |
| 在途请求等待 | 10s | 标记 503 后的缓冲期 |
