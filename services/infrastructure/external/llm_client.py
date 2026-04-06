"""
shared.llm_client — 统一 LLM 调用层
════════════════════════════════════
基于 openai SDK（兼容 DeepSeek / 其他 OpenAI-compatible 接口）

职责：
  1. 单例 AsyncOpenAI 客户端管理
  2. chat completion（非流式 / 流式）
  3. embedding 向量化
  4. token 用量统计 & 结构化返回
  5. 错误处理 & 自动重试

使用方式：
  from shared.llm_client import get_llm_client

  client = get_llm_client()
  reply = await client.chat("你好")
  chunks = client.chat_stream("你好")  # async generator
  vector = await client.embed("知识点文本")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

import structlog
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError

from config import get_settings

logger = structlog.get_logger()

# ── 数据结构 ─────────────────────────────────────────


@dataclass
class ChatMessage:
    """单条对话消息"""
    role: str  # system / user / assistant
    content: str


@dataclass
class ChatResult:
    """LLM 回复结果"""
    content: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"


@dataclass
class StreamChunk:
    """流式输出的单个片段"""
    delta: str  # 增量文本
    finish_reason: Optional[str] = None


@dataclass
class EmbeddingResult:
    """向量化结果"""
    vector: list[float]
    model_name: str
    token_count: int = 0


# ── LLM Client ───────────────────────────────────────


class LLMClient:
    """
    统一 LLM 调用客户端

    封装 openai SDK 的 AsyncOpenAI，支持：
    - DeepSeek API（OpenAI 兼容）
    - 任何 OpenAI-compatible 端点

    MVP 阶段为全局单例；后续可按模型/用途拆分实例。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str = "deepseek-chat",
        embedding_model: str = "text-embedding-v3",
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.default_model = default_model
        self.embedding_model = embedding_model

        logger.info(
            "llm_client_initialized",
            base_url=base_url,
            default_model=default_model,
            embedding_model=embedding_model,
        )

    # ── Chat Completion（非流式）────────────────────

    async def chat(
        self,
        user_content: str,
        *,
        system_prompt: Optional[str] = None,
        history: Optional[list[ChatMessage]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResult:
        """
        非流式 chat completion

        Args:
            user_content: 用户消息
            system_prompt: 系统提示词（可选）
            history: 历史消息列表（可选）
            model: 模型名（默认用 self.default_model）
            temperature: 采样温度
            max_tokens: 最大输出 token 数

        Returns:
            ChatResult 包含回复内容和 token 用量
        """
        messages = self._build_messages(user_content, system_prompt, history)
        model_name = model or self.default_model

        try:
            response = await self._client.chat.completions.create(
                model=model_name,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            choice = response.choices[0]
            usage = response.usage

            result = ChatResult(
                content=choice.message.content or "",
                model_name=response.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )

            logger.info(
                "llm_chat_completed",
                model=result.model_name,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                finish_reason=result.finish_reason,
            )
            return result

        except RateLimitError as e:
            logger.error("llm_rate_limited", error=str(e))
            raise
        except APIConnectionError as e:
            logger.error("llm_connection_error", error=str(e))
            raise
        except APIStatusError as e:
            logger.error(
                "llm_api_error",
                status_code=e.status_code,
                error=str(e),
            )
            raise

    # ── Chat Completion（流式）──────────────────────

    async def chat_stream(
        self,
        user_content: str,
        *,
        system_prompt: Optional[str] = None,
        history: Optional[list[ChatMessage]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式 chat completion（SSE 场景用）

        Usage:
            async for chunk in client.chat_stream("你好"):
                print(chunk.delta, end="", flush=True)
        """
        messages = self._build_messages(user_content, system_prompt, history)
        model_name = model or self.default_model

        try:
            stream = await self._client.chat.completions.create(
                model=model_name,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    finish = chunk.choices[0].finish_reason
                    yield StreamChunk(
                        delta=delta.content or "",
                        finish_reason=finish,
                    )

        except (RateLimitError, APIConnectionError, APIStatusError) as e:
            logger.error("llm_stream_error", error=str(e))
            raise

    # ── Embedding ──────────────────────────────────

    async def embed(
        self,
        text: str,
        *,
        model: Optional[str] = None,
    ) -> EmbeddingResult:
        """
        文本向量化

        Args:
            text: 要向量化的文本
            model: embedding 模型名（默认用 self.embedding_model）

        Returns:
            EmbeddingResult 包含向量和 token 用量
        """
        model_name = model or self.embedding_model

        try:
            response = await self._client.embeddings.create(
                model=model_name,
                input=text,
            )

            data = response.data[0]
            usage = response.usage

            result = EmbeddingResult(
                vector=data.embedding,
                model_name=response.model,
                token_count=usage.total_tokens if usage else 0,
            )

            logger.info(
                "llm_embedding_completed",
                model=result.model_name,
                vector_dim=len(result.vector),
                token_count=result.token_count,
            )
            return result

        except (RateLimitError, APIConnectionError, APIStatusError) as e:
            logger.error("llm_embedding_error", error=str(e))
            raise

    # ── 批量 Embedding ─────────────────────────────

    async def embed_batch(
        self,
        texts: list[str],
        *,
        model: Optional[str] = None,
    ) -> list[EmbeddingResult]:
        """
        批量文本向量化

        openai SDK 原生支持 list[str] 输入，一次请求完成。
        """
        if not texts:
            return []

        model_name = model or self.embedding_model

        try:
            response = await self._client.embeddings.create(
                model=model_name,
                input=texts,
            )

            usage = response.usage
            avg_tokens = (usage.total_tokens // len(texts)) if usage else 0

            results = [
                EmbeddingResult(
                    vector=item.embedding,
                    model_name=response.model,
                    token_count=avg_tokens,
                )
                for item in response.data
            ]

            logger.info(
                "llm_batch_embedding_completed",
                model=response.model,
                count=len(results),
                total_tokens=usage.total_tokens if usage else 0,
            )
            return results

        except (RateLimitError, APIConnectionError, APIStatusError) as e:
            logger.error("llm_batch_embedding_error", error=str(e))
            raise

    # ── 内部方法 ───────────────────────────────────

    @staticmethod
    def _build_messages(
        user_content: str,
        system_prompt: Optional[str],
        history: Optional[list[ChatMessage]],
    ) -> list[ChatMessage]:
        """组装消息列表：system → history → user"""
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        if history:
            messages.extend(history)
        messages.append(ChatMessage(role="user", content=user_content))
        return messages


# ── 单例管理 ──────────────────────────────────────────

_instance: Optional[LLMClient] = None


def init_llm_client(settings=None) -> LLMClient:
    """
    初始化全局 LLM Client（应在 app lifespan 中调用一次）

    如果 api_key 为空，仍会创建实例但调用时会报错 —— MVP 阶段允许
    无 key 启动（其他模块不依赖 LLM 也能正常跑）。
    """
    global _instance
    if settings is None:
        settings = get_settings()

    _instance = LLMClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        default_model=settings.llm_model,
        embedding_model=settings.llm_embedding_model,
    )
    return _instance


def get_llm_client() -> LLMClient:
    """获取全局 LLM Client 实例（未初始化则自动初始化）"""
    global _instance
    if _instance is None:
        _instance = init_llm_client()
    return _instance
