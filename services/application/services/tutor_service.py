"""
AI Tutor 业务逻辑
─────────────────
会话管理 + 消息收发 + LLM 调用
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models import Conversation, Message
from infrastructure.persistence.models.base import generate_uuid7
from shared.exceptions import ForbiddenError, NotFoundError, ValidationError

logger = structlog.get_logger()


class TutorService:
    """AI Tutor 核心服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 会话 CRUD ─────────────────────────────────────

    async def create_conversation(
        self,
        student_id: str,
        scene: str = "free_chat",
        title: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> Conversation:
        """创建新会话"""
        conv = Conversation(
            id=str(generate_uuid7()),
            student_id=student_id,
            scene=scene,
            title=title,
            context=context,
        )
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        logger.info(
            "conversation_created",
            conversation_id=str(conv.id),
            student_id=student_id,
            scene=scene,
        )
        return conv

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """获取会话（不含消息列表）"""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            raise NotFoundError("conversation", conversation_id)
        return conv

    async def list_conversations(
        self,
        student_id: Optional[str] = None,
        scene: Optional[str] = None,
        status: str = "active",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Conversation], int]:
        """会话列表（分页），管理后台可查看所有学生的会话"""
        base = select(Conversation).where(
            Conversation.deleted_at.is_(None),
            Conversation.status == status,
        )
        if student_id:
            base = base.where(Conversation.student_id == student_id)
        if scene:
            base = base.where(Conversation.scene == scene)

        # total
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # items
        items_stmt = (
            base.order_by(Conversation.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def update_conversation(
        self,
        conversation_id: str,
        **kwargs,
    ) -> Conversation:
        """更新会话字段"""
        conv = await self.get_conversation(conversation_id)
        for k, v in kwargs.items():
            if hasattr(conv, k):
                setattr(conv, k, v)
        await self.db.flush()
        await self.db.refresh(conv)
        logger.info(
            "conversation_updated",
            conversation_id=conversation_id,
            fields=list(kwargs.keys()),
        )
        return conv

    async def archive_conversation(self, conversation_id: str) -> Conversation:
        """归档会话"""
        return await self.update_conversation(conversation_id, status="archived")

    async def soft_delete_conversation(self, conversation_id: str) -> Conversation:
        """软删除会话"""
        conv = await self.get_conversation(conversation_id)
        conv.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(conv)
        logger.info("conversation_soft_deleted", conversation_id=conversation_id)
        return conv

    # ── 消息 ──────────────────────────────────────────

    async def list_messages(
        self,
        conversation_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Message], int]:
        """会话消息列表（分页，按时间正序）"""
        # 确认会话存在
        await self.get_conversation(conversation_id)

        base = select(Message).where(Message.conversation_id == conversation_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            base.order_by(Message.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def send_message(
        self,
        conversation_id: str,
        content: str,
    ) -> tuple[Message, Message]:
        """
        发送用户消息 → 调用 LLM → 返回 (user_msg, assistant_msg)

        MVP 阶段同步调用 LLM；后续可改为 SSE 流式。
        """
        conv = await self.get_conversation(conversation_id)

        if conv.status != "active":
            raise ValidationError(f"会话状态 {conv.status}，无法发送消息")

        # 1. 保存用户消息
        user_msg = Message(
            id=str(generate_uuid7()),
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        self.db.add(user_msg)

        # 2. 调用 LLM 获取回复
        ai_reply = await self._call_llm(conv, content)

        # 3. 保存 AI 回复
        assistant_msg = Message(
            id=str(generate_uuid7()),
            conversation_id=conversation_id,
            role="assistant",
            content=ai_reply["content"],
            token_count=ai_reply.get("token_count"),
            model_name=ai_reply.get("model_name"),
        )
        self.db.add(assistant_msg)

        # 4. 更新会话冗余字段
        conv.message_count += 2
        conv.last_message_at = datetime.now(timezone.utc)

        # 5. 自动生成标题（首次对话）
        if conv.message_count == 2 and not conv.title:
            conv.title = content[:50]

        await self.db.flush()

        logger.info(
            "message_sent",
            conversation_id=conversation_id,
            user_msg_id=str(user_msg.id),
            assistant_msg_id=str(assistant_msg.id),
            token_count=ai_reply.get("token_count"),
        )
        return user_msg, assistant_msg

    async def _call_llm(self, conv: Conversation, user_content: str) -> dict:
        """
        调用 LLM：构建 system prompt → 加载历史消息 → 调用 LLMClient

        流程：
        1. 根据 scene 构建 system prompt
        2. 加载最近 N 条历史消息作为上下文
        3. 调用 LLMClient.chat() 获取回复
        """
        from infrastructure.external.llm_client import get_llm_client, ChatMessage

        llm = get_llm_client()

        # 1. 构建 system prompt
        system_prompt = self._build_system_prompt(conv)

        # 2. 加载历史消息（最近 20 条，避免超 token 限制）
        history = await self._load_history(conv.id, limit=20)

        # 3. 调用 LLM
        try:
            result = await llm.chat(
                user_content=user_content,
                system_prompt=system_prompt,
                history=history,
                temperature=0.7,
                max_tokens=2048,
            )

            logger.info(
                "llm_call_completed",
                conversation_id=str(conv.id),
                scene=conv.scene,
                model=result.model_name,
                total_tokens=result.total_tokens,
            )

            return {
                "content": result.content,
                "token_count": result.total_tokens,
                "model_name": result.model_name,
            }

        except Exception as e:
            # LLM 调用失败时降级为错误提示，不抛异常中断对话
            logger.error(
                "llm_call_failed",
                conversation_id=str(conv.id),
                error=str(e),
                exc_info=True,
            )
            return {
                "content": "抱歉，AI 暂时无法响应，请稍后再试。",
                "token_count": 0,
                "model_name": "error_fallback",
            }

    def _build_system_prompt(self, conv: Conversation) -> str:
        """根据会话场景构建 system prompt"""
        # 基础人设
        base = (
            "你是「知趣课堂」的AI辅导老师，专注于帮助中小学生课后学习。"
            "你的回答应当准确、易懂、有耐心。"
            "如果不确定答案，请诚实说明，不要编造内容。"
        )

        # 场景特化指令
        scene_prompts = {
            "free_chat": "学生正在自由提问，你可以回答学习相关的各类问题。",
            "homework_help": (
                "学生正在寻求作业帮助。请引导学生思考，不要直接给出完整答案。"
                "先帮助学生理解题目，提示解题思路，再逐步引导。"
            ),
            "concept_explain": (
                "学生需要概念讲解。请用简洁易懂的语言解释概念，"
                "适当举例说明，必要时类比生活场景帮助理解。"
            ),
            "review_guide": (
                "学生正在复习。请帮助学生梳理知识要点，"
                "总结关键概念，必要时用思维导图式的结构化方式呈现。"
            ),
            "error_analysis": (
                "学生遇到了做错的题目。请分析错误原因，"
                "找出知识盲点，给出正确的解题思路和方法。"
            ),
        }

        scene_instruction = scene_prompts.get(conv.scene, scene_prompts["free_chat"])

        # 上下文信息（如果有）
        ctx_parts = []
        if conv.context:
            if conv.context.get("student_grade"):
                ctx_parts.append(f"学生年级：{conv.context['student_grade']}")
            if conv.context.get("difficulty"):
                ctx_parts.append(f"难度偏好：{conv.context['difficulty']}/5")
            if conv.context.get("system_prompt_override"):
                # 允许任务指定自定义 prompt 覆盖
                return conv.context["system_prompt_override"]

        ctx_str = "；".join(ctx_parts)
        context_line = f"\n学生信息：{ctx_str}" if ctx_str else ""

        return f"{base}\n{scene_instruction}{context_line}"

    async def _load_history(
        self, conversation_id: str, limit: int = 20
    ) -> list:
        """加载最近 N 条历史消息，转为 ChatMessage 列表"""
        from infrastructure.external.llm_client import ChatMessage

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # 时间正序

        return [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in messages
            if msg.role in ("user", "assistant")
        ]

    async def get_message(self, message_id: str) -> Message:
        """获取单条消息"""
        stmt = select(Message).where(Message.id == message_id)
        result = await self.db.execute(stmt)
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundError("message", message_id)
        return msg

    # ── 路由适配器 ────────────────────────────────────

    async def send_and_reply(
        self,
        conversation_id: str,
        content: str,
        role: str = "user",
    ) -> tuple[Message, Message]:
        """send_message 的路由适配别名"""
        return await self.send_message(conversation_id, content)

    async def send_and_reply_stream(
        self,
        conversation_id: str,
        content: str,
        role: str = "user",
    ):
        """流式回复 — MVP stub，暂回退到同步调用"""
        _user_msg, assistant_msg = await self.send_message(
            conversation_id, content,
        )
        # 模拟单块 SSE 事件
        yield f"data: {assistant_msg.content}\n\n"
        yield "data: [DONE]\n\n"

    async def add_feedback(
        self, *, message_id, data,
    ) -> dict:
        """消息反馈 — MVP stub，将反馈记录到日志"""
        msg = await self.get_message(str(message_id))
        rating = getattr(data, "rating", None)
        comment = getattr(data, "comment", None)
        logger.info(
            "message_feedback",
            message_id=str(message_id),
            rating=rating,
            comment=comment,
        )
        return {
            "message_id": str(msg.id),
            "rating": rating,
            "comment": comment,
            "status": "recorded",
        }
