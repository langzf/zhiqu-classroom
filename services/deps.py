"""公共依赖注入 — FastAPI Depends"""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from database import get_db
from shared.exceptions import UnauthorizedError, ForbiddenError
from shared.security import JWTManager, TokenPayload
import jwt as pyjwt


# ── 类型别名 ──

DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


# ── JWT 依赖 ──

def get_jwt_manager(settings: AppSettings) -> JWTManager:
    return JWTManager(settings.jwt_secret, settings.jwt_algorithm)


JwtManager = Annotated[JWTManager, Depends(get_jwt_manager)]


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    jwt_mgr: JwtManager = None,  # type: ignore[assignment]
) -> TokenPayload:
    """从 Authorization header 提取并验证 JWT"""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("missing or invalid authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt_mgr.get_payload(token)
    except pyjwt.ExpiredSignatureError:
        raise UnauthorizedError("token expired")
    except pyjwt.InvalidTokenError:
        raise UnauthorizedError("invalid token")

    return payload


CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


def require_role(*roles: str):
    """
    角色权限校验依赖工厂。

    返回一个 async 闭包函数，用于 Depends(require_role("admin"))。
    """
    async def _check(user: CurrentUser) -> TokenPayload:
        if user.role not in roles:
            raise ForbiddenError(f"requires role: {', '.join(roles)}")
        return user
    return _check


# 常用角色校验（可直接用于 Depends）
AdminUser = Annotated[TokenPayload, Depends(require_role("admin"))]
StudentUser = Annotated[TokenPayload, Depends(require_role("student"))]
GuardianUser = Annotated[TokenPayload, Depends(require_role("guardian"))]

# 便捷别名 — 返回闭包函数（用于 Depends(require_admin)）
require_admin = require_role("admin")
require_student = require_role("student")
require_guardian = require_role("guardian")
