"""模型供应商适配器 — 策略模式

每个供应商实现 BaseProviderAdapter 接口，统一 chat / chat_stream / embed / test_connection。
工厂函数 get_adapter() 根据 provider_type 返回对应适配器。
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Sequence

import structlog

logger = structlog.get_logger()


# ── 公共数据结构 ──────────────────────────────────────

@dataclass
class ChatMessage:
    role: str  # system / user / assistant / tool
    content: str
    name: Optional[str] = None


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResult:
    content: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = ""
    latency_ms: float = 0.0


@dataclass
class StreamChunk:
    delta: str = ""
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


@dataclass
class EmbeddingResult:
    embeddings: list[list[float]] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""


@dataclass
class ProviderCredentials:
    """供应商凭据，由 Service 层解密后传入"""
    api_key: str
    base_url: Optional[str] = None
    organization: Optional[str] = None


# ── 基类 ──────────────────────────────────────────────

class BaseProviderAdapter(abc.ABC):
    """供应商适配器抽象基类"""

    provider_type: str

    def __init__(self, credentials: ProviderCredentials):
        self.credentials = credentials

    @abc.abstractmethod
    async def chat(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResult:
        """非流式对话"""

    @abc.abstractmethod
    async def chat_stream(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """流式对话"""

    async def embed(
        self,
        texts: Sequence[str],
        model: str,
        **kwargs,
    ) -> EmbeddingResult:
        """文本向量化（不是所有供应商都支持）"""
        raise NotImplementedError(f"{self.provider_type} 不支持 embedding")

    async def test_connection(self, model: str) -> bool:
        """连接测试"""
        try:
            result = await self.chat(
                [ChatMessage(role="user", content="hi")],
                model=model,
                max_tokens=5,
            )
            return bool(result.content)
        except Exception as e:
            logger.warning("provider_connection_test_failed",
                           provider_type=self.provider_type, error=str(e))
            return False


# ── OpenAI / OpenAI Compatible ────────────────────────

class OpenAIAdapter(BaseProviderAdapter):
    """适配 OpenAI 及所有 OpenAI-compatible 接口（DeepSeek, Together, vLLM 等）"""

    provider_type = "openai"

    def _get_client(self):
        from openai import AsyncOpenAI
        kwargs = {"api_key": self.credentials.api_key}
        if self.credentials.base_url:
            kwargs["base_url"] = self.credentials.base_url
        if self.credentials.organization:
            kwargs["organization"] = self.credentials.organization
        return AsyncOpenAI(**kwargs)

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResult:
        client = self._get_client()
        msgs = [{"role": m.role, "content": m.content} for m in messages]

        params = {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update(kwargs)

        start = time.monotonic()
        try:
            resp = await client.chat.completions.create(**params)
        finally:
            await client.close()

        latency = (time.monotonic() - start) * 1000
        choice = resp.choices[0]
        usage = TokenUsage(
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
        )
        return ChatResult(
            content=choice.message.content or "",
            usage=usage,
            model=resp.model,
            finish_reason=choice.finish_reason or "",
            latency_ms=latency,
        )

    async def chat_stream(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        client = self._get_client()
        msgs = [{"role": m.role, "content": m.content} for m in messages]

        params = {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update(kwargs)

        try:
            stream = await client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    yield StreamChunk(
                        delta=delta.content or "",
                        finish_reason=chunk.choices[0].finish_reason,
                    )
        finally:
            await client.close()

    async def embed(
        self,
        texts: Sequence[str],
        model: str,
        **kwargs,
    ) -> EmbeddingResult:
        client = self._get_client()
        try:
            resp = await client.embeddings.create(
                model=model,
                input=list(texts),
                **kwargs,
            )
        finally:
            await client.close()

        vectors = [item.embedding for item in resp.data]
        usage = TokenUsage(
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
        )
        return EmbeddingResult(embeddings=vectors, usage=usage, model=resp.model)


# ── Anthropic ─────────────────────────────────────────

class AnthropicAdapter(BaseProviderAdapter):
    """适配 Anthropic Claude 系列"""

    provider_type = "anthropic"

    def _get_client(self):
        from anthropic import AsyncAnthropic
        kwargs = {"api_key": self.credentials.api_key}
        if self.credentials.base_url:
            kwargs["base_url"] = self.credentials.base_url
        return AsyncAnthropic(**kwargs)

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResult:
        client = self._get_client()

        # Anthropic 的 system 消息单独传入
        system_text = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_text += m.content + "\n"
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        params = {
            "model": model,
            "messages": chat_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_text.strip():
            params["system"] = system_text.strip()
        params.update(kwargs)

        start = time.monotonic()
        try:
            resp = await client.messages.create(**params)
        finally:
            await client.close()

        latency = (time.monotonic() - start) * 1000
        content = ""
        if resp.content:
            content = resp.content[0].text if hasattr(resp.content[0], "text") else ""

        usage = TokenUsage(
            prompt_tokens=resp.usage.input_tokens if resp.usage else 0,
            completion_tokens=resp.usage.output_tokens if resp.usage else 0,
            total_tokens=(
                (resp.usage.input_tokens + resp.usage.output_tokens) if resp.usage else 0
            ),
        )
        return ChatResult(
            content=content,
            usage=usage,
            model=resp.model,
            finish_reason=resp.stop_reason or "",
            latency_ms=latency,
        )

    async def chat_stream(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        client = self._get_client()

        system_text = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_text += m.content + "\n"
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        params = {
            "model": model,
            "messages": chat_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }
        if system_text.strip():
            params["system"] = system_text.strip()
        params.update(kwargs)

        try:
            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(delta=text)
                # 最后一个 chunk 带 finish_reason
                final = await stream.get_final_message()
                usage = TokenUsage(
                    prompt_tokens=final.usage.input_tokens,
                    completion_tokens=final.usage.output_tokens,
                    total_tokens=final.usage.input_tokens + final.usage.output_tokens,
                )
                yield StreamChunk(
                    delta="",
                    finish_reason=final.stop_reason or "end_turn",
                    usage=usage,
                )
        finally:
            await client.close()


# ── 适配器注册表 & 工厂 ──────────────────────────────

_ADAPTER_REGISTRY: dict[str, type[BaseProviderAdapter]] = {
    "openai": OpenAIAdapter,
    "openai_compatible": OpenAIAdapter,  # 复用 OpenAI 适配器
    "anthropic": AnthropicAdapter,
    "qwen": OpenAIAdapter,  # 通义千问兼容 OpenAI 接口
    "deepseek": OpenAIAdapter,  # DeepSeek 兼容 OpenAI 接口
}


def get_adapter(
    provider_type: str,
    credentials: ProviderCredentials,
) -> BaseProviderAdapter:
    """根据 provider_type 获取适配器实例"""
    adapter_cls = _ADAPTER_REGISTRY.get(provider_type)
    if adapter_cls is None:
        raise ValueError(f"不支持的供应商类型: {provider_type}")
    adapter = adapter_cls(credentials)
    adapter.provider_type = provider_type
    return adapter


def list_supported_providers() -> list[str]:
    """列出所有已注册的 provider_type"""
    return sorted(set(_ADAPTER_REGISTRY.keys()))
