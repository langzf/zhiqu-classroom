"""模型配置模块 Schema — 请求 / 响应"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from interfaces.schemas.base import IdTimestampSchema, OrmBase


# ── ModelProvider ─────────────────────────────────────

class ModelProviderCreate(BaseModel):
    name: str = Field(..., max_length=100, description="供应商显示名")
    provider_type: str = Field(
        ..., max_length=30,
        description="供应商类型: openai / anthropic / qwen / openai_compatible / deepseek / local",
    )
    base_url: Optional[str] = Field(None, max_length=500, description="API Base URL")
    api_key: str = Field(..., min_length=1, description="API Key（明文传入，服务端加密存储）")
    extra_config: Optional[dict] = Field(
        None, description="供应商级别额外配置 (如 organization, Anthropic version 等)"
    )
    is_active: bool = Field(True, description="是否启用")
    sort_order: int = Field(0, description="排序权重")


class ModelProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    provider_type: Optional[str] = Field(None, max_length=30)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, min_length=1, description="传入时更新，不传不修改")
    extra_config: Optional[dict] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ModelProviderOut(IdTimestampSchema):
    name: str
    provider_type: str
    base_url: Optional[str] = None
    api_key_masked: str = Field("", description="掩码后的 API Key（由 Service 层生成）")
    extra_config: Optional[dict] = None
    is_active: bool
    sort_order: int


class ModelProviderDetail(ModelProviderOut):
    """详情（含关联模型配置列表）"""
    model_configs: list[ModelConfigOut] = Field(default_factory=list)


# ── ModelConfig ───────────────────────────────────────

class ModelConfigCreate(BaseModel):
    provider_id: UUID = Field(..., description="所属供应商 ID")
    model_name: str = Field(..., max_length=100, description="模型标识，如 gpt-4o")
    display_name: str = Field(..., max_length=100, description="前端显示名称")
    capabilities: list[str] = Field(
        default_factory=lambda: ["chat"],
        description="能力标签: chat / vision / embedding / tts / stt / function_calling",
    )
    default_params: dict = Field(
        default_factory=dict,
        description="默认参数: temperature, max_tokens 等",
    )
    is_active: bool = Field(True)
    sort_order: int = Field(0)


class ModelConfigUpdate(BaseModel):
    provider_id: Optional[UUID] = None
    model_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    capabilities: Optional[list[str]] = None
    default_params: Optional[dict] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ModelConfigOut(IdTimestampSchema):
    provider_id: UUID
    model_name: str
    display_name: str
    capabilities: list[str]
    default_params: dict
    is_active: bool
    sort_order: int


class ModelConfigDetail(ModelConfigOut):
    """详情（含供应商信息）"""
    provider: Optional[ModelProviderOut] = None


# ── SceneModelBinding ─────────────────────────────────

class SceneModelBindingCreate(BaseModel):
    scene_key: str = Field(..., max_length=100, description="场景标识，如 content.parse_textbook")
    scene_label: Optional[str] = Field(None, max_length=200, description="场景中文描述")
    model_config_id: UUID = Field(..., description="绑定的模型配置 ID")
    param_overrides: dict = Field(
        default_factory=dict,
        description="参数覆盖: temperature, max_tokens 等",
    )
    is_active: bool = Field(True)


class SceneModelBindingUpdate(BaseModel):
    scene_label: Optional[str] = Field(None, max_length=200)
    model_config_id: Optional[UUID] = None
    param_overrides: Optional[dict] = None
    is_active: Optional[bool] = None


class SceneModelBindingOut(IdTimestampSchema):
    scene_key: str
    scene_label: Optional[str] = None
    model_config_id: UUID
    param_overrides: dict
    is_active: bool


class SceneModelBindingDetail(SceneModelBindingOut):
    """详情（含完整模型配置 + 供应商信息）"""
    model_config_info: Optional[ModelConfigDetail] = None


# ── ResolvedModel（业务调用时使用） ────────────────────

class ResolvedModel(BaseModel):
    """场景解析后的完整模型配置，供业务代码直接使用"""
    scene_key: str
    provider_type: str
    model_name: str
    api_key: str = Field(exclude=True)  # 不序列化到响应
    base_url: Optional[str] = None
    extra_config: Optional[dict] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    extra_params: dict = Field(default_factory=dict)


# 处理前向引用
ModelProviderDetail.model_rebuild()
