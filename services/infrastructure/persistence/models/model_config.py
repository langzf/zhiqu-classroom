"""
模型配置相关 ORM 模型

三层结构:
  ModelProvider  (供应商: OpenAI / Anthropic / DeepSeek / ...)
  └── ModelConfig  (具体模型: gpt-4o / claude-3.5-sonnet / ...)
      └── SceneModelBinding  (场景绑定: 教材解析用模型A, 知识点提取用模型B)
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid7


# ── 供应商类型枚举值 ──────────────────────────────────────────
# 存为字符串而非 PG enum, 方便扩展
PROVIDER_TYPES = (
    "openai",               # OpenAI 官方
    "openai_compatible",    # 兼容 OpenAI 接口的第三方 (DeepSeek, 零一万物, Groq...)
    "anthropic",            # Anthropic Claude
    "google",               # Google Gemini
    "qwen",                 # 通义千问 (DashScope)
    "local",                # 本地部署 (Ollama, vLLM, text-generation-webui)
)

# ── 模型能力标签 ─────────────────────────────────────────────
CAPABILITIES = ("chat", "vision", "embedding", "tts", "stt", "function_calling")


class ModelProvider(Base):
    """模型供应商 — 如 OpenAI / Anthropic / DeepSeek"""

    __tablename__ = "model_providers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="显示名称")
    provider_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="供应商类型"
    )
    base_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="API 基础地址"
    )
    api_key_enc: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="加密后的 API Key"
    )
    extra_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="供应商级别额外配置 (如 Anthropic version header, Azure deployment 等)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # relationships
    models: Mapped[list[ModelConfig]] = relationship(
        "ModelConfig", back_populates="provider", cascade="all, delete-orphan"
    )


class ModelConfig(Base):
    """具体模型配置 — 如 gpt-4o / claude-3-5-sonnet"""

    __tablename__ = "model_configs"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_name", name="uq_provider_model"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    provider_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("model_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="模型标识 (传给 API 的值)"
    )
    display_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="前端显示名称"
    )
    capabilities: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: ["chat"],
        comment='能力标签: ["chat","vision","embedding","tts","stt","function_calling"]'
    )
    default_params: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="默认调用参数: {temperature, max_tokens, top_p, ...}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # relationships
    provider: Mapped[ModelProvider] = relationship("ModelProvider", back_populates="models")
    scene_bindings: Mapped[list[SceneModelBinding]] = relationship(
        "SceneModelBinding", back_populates="model_config"
    )


class SceneModelBinding(Base):
    """场景-模型绑定 — 哪个业务场景使用哪个模型"""

    __tablename__ = "scene_model_bindings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid7
    )
    scene_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False,
        comment="场景标识, 如 content.parse_textbook"
    )
    scene_label: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="场景中文描述"
    )
    model_config_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("model_configs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    param_overrides: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="覆盖模型默认参数 (针对此场景的特殊调优)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # relationships
    model_config: Mapped[ModelConfig] = relationship(
        "ModelConfig", back_populates="scene_bindings"
    )
