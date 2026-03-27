"""应用配置 — 从环境变量加载"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，支持 .env 文件和环境变量"""

    # ── App ──
    app_name: str = "zhiqu-classroom"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Database ──
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/zhiqu"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── MinIO ──
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "zhiqu"
    minio_secure: bool = False

    # ── JWT ──
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # ── LLM ──
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_embedding_model: str = "text-embedding-v3"
    llm_embedding_dim: int = 1024

    # ── SMS ──
    sms_provider: str = "mock"  # mock / aliyun
    sms_access_key: str = ""
    sms_secret_key: str = ""
    sms_sign_name: str = "知趣课堂"
    sms_template_code: str = ""

    # ── CORS ──
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
