"""统一依赖注入 — FastAPI Depends 别名"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from infrastructure.persistence.database import get_db
from shared.exceptions import ForbiddenError, UnauthorizedError
from shared.security import JWTManager, TokenPayload

from application.services.content_service import ContentService
from application.services.exercise_service import ExerciseService
from application.services.learning_service import LearningService
from application.services.learning_core_service import LearningCoreService
from application.services.prompt_service import PromptService
from application.services.tutor_service import TutorService
from application.services.user_service import UserService


# ── Settings & JWT ────────────────────────────────────

AppSettings = Annotated[Settings, Depends(get_settings)]


def _get_jwt_manager(settings: AppSettings) -> JWTManager:
    return JWTManager(secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)


JwtManager = Annotated[JWTManager, Depends(_get_jwt_manager)]

# ── DB Session ────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── 当前用户 ──────────────────────────────────────────

async def _get_current_user(
    jwt: JwtManager,
    authorization: str = Header(..., alias="Authorization"),
) -> TokenPayload:
    """从 Authorization: Bearer <token> 提取并验证用户身份"""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("无效的认证格式")
    token = authorization.removeprefix("Bearer ").strip()
    payload = jwt.get_payload(token)
    if payload is None:
        raise UnauthorizedError("Token 无效或已过期")
    return payload


CurrentUser = Annotated[TokenPayload, Depends(_get_current_user)]


# ── 角色工厂 ──────────────────────────────────────────

def require_role(*roles: str):
    """返回一个依赖闭包，校验用户角色"""
    async def _checker(user: CurrentUser) -> TokenPayload:
        if user.role not in roles:
            raise ForbiddenError(f"需要角色: {', '.join(roles)}")
        return user
    return _checker


AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]
StudentUser = Annotated[TokenPayload, Depends(require_role("student"))]
GuardianUser = Annotated[TokenPayload, Depends(require_role("guardian"))]


# ── Service 工厂 ──────────────────────────────────────

def _content_svc(db: DbSession) -> ContentService:
    return ContentService(db=db)

def _exercise_svc(db: DbSession) -> ExerciseService:
    return ExerciseService(db=db)

def _learning_svc(db: DbSession) -> LearningService:
    return LearningService(db=db)

def _learning_core_svc(db: DbSession) -> LearningCoreService:
    return LearningCoreService(db=db)

def _prompt_svc(db: DbSession) -> PromptService:
    return PromptService(db=db)

def _tutor_svc(db: DbSession) -> TutorService:
    return TutorService(db=db)

def _user_svc(db: DbSession) -> UserService:
    return UserService(db=db)


ContentSvc = Annotated[ContentService, Depends(_content_svc)]
ExerciseSvc = Annotated[ExerciseService, Depends(_exercise_svc)]
LearningSvc = Annotated[LearningService, Depends(_learning_svc)]
LearningCoreSvc = Annotated[LearningCoreService, Depends(_learning_core_svc)]
PromptSvc = Annotated[PromptService, Depends(_prompt_svc)]
TutorSvc = Annotated[TutorService, Depends(_tutor_svc)]
UserSvc = Annotated[UserService, Depends(_user_svc)]
