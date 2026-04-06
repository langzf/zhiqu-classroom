"""
习题生成 业务逻辑
──────────────────
基于知识点 + Prompt 模板 → 调用 LLM 生成练习题
"""

from __future__ import annotations

import json
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models import (
    GeneratedResource,
    KnowledgePoint,
    PromptTemplate,
)
from infrastructure.persistence.models.base import generate_uuid7
from shared.exceptions import NotFoundError, BusinessError

logger = structlog.get_logger()


class ExerciseService:
    """习题生成服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_exercises(
        self,
        knowledge_point_ids: list[str],
        count: int = 5,
        difficulty: Optional[int] = None,
        exercise_type: str = "choice",
        template_code: Optional[str] = None,
    ) -> list[dict]:
        """
        根据知识点生成练习题

        1. 加载知识点信息
        2. 查找/使用 prompt 模板
        3. 调用 LLM 生成
        4. 保存到 generated_resources
        5. 返回结果
        """
        from infrastructure.external.llm_client import get_llm_client

        llm = get_llm_client()

        # 1. 加载知识点
        kps = []
        for kp_id in knowledge_point_ids:
            stmt = select(KnowledgePoint).where(KnowledgePoint.id == kp_id)
            result = await self.db.execute(stmt)
            kp = result.scalar_one_or_none()
            if not kp:
                raise NotFoundError("knowledge_point", kp_id)
            kps.append(kp)

        # 2. 构建 prompt
        prompt = await self._build_prompt(
            kps,
            count=count,
            difficulty=difficulty or kps[0].difficulty,
            exercise_type=exercise_type,
            template_code=template_code,
        )

        # 3. 调用 LLM
        try:
            result = await llm.chat(
                user_content=prompt,
                system_prompt=(
                    "你是一个专业的教育内容生成助手。"
                    "请严格按照 JSON 格式输出练习题。"
                ),
                temperature=0.8,
                max_tokens=4096,
            )

            exercises = self._parse_exercises(result.content)

        except Exception as e:
            logger.error(
                "exercise_generation_failed",
                kp_ids=knowledge_point_ids,
                error=str(e),
            )
            raise BusinessError(f"习题生成失败：{e}")

        # 4. 保存到 generated_resources
        saved = []
        for ex in exercises:
            resource = GeneratedResource(
                id=str(generate_uuid7()),
                knowledge_point_id=kps[0].chapter_id,  # 关联章节
                resource_type="exercise",
                content=ex,
                model_name=result.model_name,
                token_count=result.total_tokens // max(len(exercises), 1),
            )
            self.db.add(resource)
            saved.append(ex)

        await self.db.flush()

        logger.info(
            "exercises_generated",
            count=len(saved),
            kp_ids=knowledge_point_ids,
            type=exercise_type,
        )
        return saved

    async def _build_prompt(
        self,
        kps: list[KnowledgePoint],
        count: int,
        difficulty: int,
        exercise_type: str,
        template_code: Optional[str] = None,
    ) -> str:
        """构建习题生成 prompt"""
        # 尝试使用模板
        if template_code:
            stmt = select(PromptTemplate).where(
                PromptTemplate.code == template_code,
                PromptTemplate.is_active.is_(True),
            )
            result = await self.db.execute(stmt)
            tpl = result.scalar_one_or_none()
            if tpl:
                return tpl.content.format(
                    knowledge_points="\n".join(kp.name for kp in kps),
                    count=count,
                    difficulty=difficulty,
                    exercise_type=exercise_type,
                )

        # 默认 prompt
        kp_desc = "\n".join(
            f"- {kp.name}（难度 {kp.difficulty}/5）" for kp in kps
        )
        difficulty_map = {1: "简单", 2: "较简单", 3: "中等", 4: "较难", 5: "困难"}
        diff_label = difficulty_map.get(difficulty, "中等")
        type_map = {
            "choice": "选择题（单选）",
            "multi_choice": "多选题",
            "fill_blank": "填空题",
            "short_answer": "简答题",
            "true_false": "判断题",
        }
        type_label = type_map.get(exercise_type, exercise_type)

        return f"""请根据以下知识点生成 {count} 道{type_label}。

知识点：
{kp_desc}

难度要求：{diff_label}（{difficulty}/5）

请以 JSON 数组格式输出，每道题包含：
- question: 题目内容
- options: 选项列表（如选择题）
- answer: 正确答案
- explanation: 解题思路
- difficulty: 难度（1-5）
- knowledge_point: 关联的知识点名称

输出示例：
[{{"question": "...", "options": ["A. ...", "B. ..."], "answer": "A", "explanation": "...", "difficulty": 3, "knowledge_point": "..."}}]"""

    def _parse_exercises(self, content: str) -> list[dict]:
        """解析 LLM 输出的练习题 JSON"""
        # 尝试从 markdown code block 中提取
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            data = json.loads(content.strip())
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "exercises" in data:
                return data["exercises"]
            return [data]
        except json.JSONDecodeError:
            logger.warning("exercise_parse_failed", content=content[:200])
            return [{"raw_content": content, "parse_error": True}]
