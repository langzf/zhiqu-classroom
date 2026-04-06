"""interfaces.schemas — Schema 统一入口"""

# ── 基类 ──
from interfaces.schemas.base import OrmBase, IdTimestampSchema  # noqa: F401

# ── AI Tutor ──
from interfaces.schemas.tutor import (  # noqa: F401
    ConversationCreate,
    ConversationUpdate,
    ConversationOut,
    MessageSend,
    MessageOut,
    FeedbackCreate,
)

# ── Content Engine ──
from interfaces.schemas.content import (  # noqa: F401
    TextbookCreate,
    TextbookUpdate,
    TextbookOut,
    TextbookDetail,
    ChapterOut,
    ChapterTree,
    KnowledgePointOut,
    KnowledgePointCreate,
    KpSearchRequest,
    GeneratedResourceOut,
    GenerateResourceRequest,
    ExerciseGenerateRequest,
    ExerciseCreate,
    ExerciseOut,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateOut,
)

# ── Learning (Orchestrator + Core) ──
from interfaces.schemas.learning import (  # noqa: F401
    TaskItemCreate,
    TaskCreate,
    TaskUpdate,
    TaskItemOut,
    TaskOut,
    TaskDetail,
    ProgressStart,
    ProgressItemSubmit,
    ProgressSubmit,
    ProgressOut,
    LearningTaskCreate,
    LearningTaskUpdate,
    LearningTaskOut,
    MasteryRecordOut,
    StudySessionCreate,
    StudySessionOut,
)

# ── User Profile ──
from interfaces.schemas.user import (  # noqa: F401
    UserCreate,
    UserUpdate,
    AdminUserUpdate,
    UserOut,
    GuardianBindingCreate,
    GuardianBindingOut,
    LoginRequest,
    TokenOut,
    RegisterRequest,
)
