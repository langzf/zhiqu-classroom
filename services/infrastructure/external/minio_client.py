"""
MinIO 客户端 — 文件存储封装
═══════════════════════════
提供全局 MinIO 客户端初始化 + 上传/下载辅助函数。
注意：minio SDK 是同步的，在 async 端点中通过 run_in_executor 调用。
"""

from __future__ import annotations

import asyncio
from functools import partial
from io import BytesIO
from typing import TYPE_CHECKING

import structlog
from minio import Minio
from minio.error import S3Error

if TYPE_CHECKING:
    from config import Settings

logger = structlog.get_logger()

# ── 全局单例 ──────────────────────────────────────────

_client: Minio | None = None
_bucket: str = ""


def init_minio(settings: Settings) -> Minio:
    """应用启动时调用，初始化 MinIO 客户端并确保 bucket 存在。"""
    global _client, _bucket

    _client = Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    _bucket = settings.minio_bucket

    # 确保 bucket 存在
    if not _client.bucket_exists(_bucket):
        _client.make_bucket(_bucket)
        logger.info("minio_bucket_created", bucket=_bucket)
    else:
        logger.info("minio_bucket_exists", bucket=_bucket)

    logger.info(
        "minio_initialized",
        endpoint=settings.minio_endpoint,
        bucket=_bucket,
    )
    return _client


def get_minio() -> Minio:
    """获取全局 MinIO 客户端，未初始化则抛异常。"""
    if _client is None:
        raise RuntimeError("MinIO not initialized — call init_minio() in lifespan")
    return _client


def get_bucket() -> str:
    """获取当前 bucket 名称。"""
    if not _bucket:
        raise RuntimeError("MinIO not initialized — call init_minio() in lifespan")
    return _bucket


# ── 同步辅助函数（供 run_in_executor 调用）────────────


def _upload_sync(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """同步上传文件到 MinIO，返回 object_name。"""
    client = get_minio()
    bucket = get_bucket()
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logger.info(
        "minio_upload_ok",
        bucket=bucket,
        object_name=object_name,
        size=len(data),
    )
    return object_name


def _download_sync(object_name: str) -> bytes:
    """同步从 MinIO 下载文件，返回 bytes。"""
    client = get_minio()
    bucket = get_bucket()
    response = client.get_object(bucket_name=bucket, object_name=object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


# ── 异步包装（端点直接调用这些）────────────────────────


async def upload_file(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """异步上传文件到 MinIO。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(_upload_sync, object_name, data, content_type),
    )


async def download_file(object_name: str) -> bytes:
    """异步从 MinIO 下载文件。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download_sync, object_name)
