"""
ORM 模型汇总 — 在此导入所有模型以确保 Alembic / metadata.create_all 能发现它们。
"""

from infrastructure.persistence.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid7

# ── tutor ──
from infrastructure.persistence.models.tutor import Conversation, Message

# ── content ──
from infrastructure.persistence.models.content import (
    Textbook,
    Chapter,
    KnowledgePoint,
    KpEmbedding,
    GeneratedResource,
    PromptTemplate,
)

# ── learning ──
from infrastructure.persistence.models.learning import (
    Task,
    TaskItem,
    TaskProgress,
    LearningTask,
    StudySession,
    MasteryRecord,
)

# ── user ──
from infrastructure.persistence.models.user import (
    User,
    StudentProfile,
    UserOAuthBinding,
    GuardianBinding,
)

__all__ = [
    # base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "generate_uuid7",
    # tutor
    "Conversation",
    "Message",
    # content
    "Textbook",
    "Chapter",
    "KnowledgePoint",
    "KpEmbedding",
    "GeneratedResource",
    "PromptTemplate",
    # learning
    "Task",
    "TaskItem",
    "TaskProgress",
    "LearningTask",
    "StudySession",
    "MasteryRecord",
    # user
    "User",
    "StudentProfile",
    "UserOAuthBinding",
    "GuardianBinding",
]
