"""
user_profile 业务逻辑
─────────────────────
用户注册/登录、个人信息、家长绑定。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from shared.base_model import generate_uuid7
from shared.exceptions import NotFoundError, ValidationError

from .models import GuardianBinding, User

logger = structlog.get_logger(__name__)


class UserService:
    """用户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 注册 / 登录 ──────────────────────────────────

    async def register(
        self,
        phone: str,
        nickname: str,
        role: str = "student",
    ) -> User:
        """注册新用户"""
        existing = await self._get_by_phone(phone)
        if existing:
            raise ValidationError("手机号已注册")

        user = User(
            phone=phone,
            nickname=nickname,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def login(self, phone: str) -> dict:
        """
        手机号登录（MVP 跳过验证码校验，直接签发 token）。
        """
        user = await self._get_by_phone(phone)
        if not user:
            raise NotFoundError("用户不存在")
        if not user.is_active:
            raise ValidationError("账号已禁用")

        access_token = self._sign_token(user)
        refresh_token = self._sign_refresh_token(user)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": user,
        }

    # ── 用户 CRUD ─────────────────────────────────────

    async def get_user(self, user_id: str) -> User:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        return user

    async def update_user(self, user_id: str, **kwargs) -> User:
        user = await self.get_user(user_id)
        for k, v in kwargs.items():
            if hasattr(user, k) and v is not None:
                setattr(user, k, v)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # ── 家长绑定 ──────────────────────────────────────

    async def bind_guardian(
        self,
        guardian_id: str,
        student_id: str,
        relation: str = "parent",
    ) -> GuardianBinding:
        """绑定家长和学生"""
        await self.get_user(guardian_id)
        await self.get_user(student_id)

        # 检查是否已绑定
        stmt = select(GuardianBinding).where(
            GuardianBinding.guardian_id == guardian_id,
            GuardianBinding.student_id == student_id,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValidationError("已绑定")

        binding = GuardianBinding(
            guardian_id=guardian_id,
            student_id=student_id,
            relationship_type=relation,
        )
        self.db.add(binding)
        await self.db.flush()
        await self.db.refresh(binding)
        return binding

    async def list_children(self, guardian_id: str) -> list[User]:
        """获取家长绑定的所有学生"""
        stmt = (
            select(User)
            .join(GuardianBinding, GuardianBinding.student_id == User.id)
            .where(
                GuardianBinding.guardian_id == guardian_id,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── 内部方法 ──────────────────────────────────────

    async def _get_by_phone(self, phone: str) -> Optional[User]:
        stmt = select(User).where(User.phone == phone, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _sign_token(self, user: User) -> str:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(days=1),
            "jti": str(generate_uuid7()),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    def _sign_refresh_token(self, user: User) -> str:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(days=7),
            "jti": str(generate_uuid7()),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """用 refresh_token 换取新的 access_token"""
        settings = get_settings()
        try:
            payload = jwt.decode(
                refresh_token, settings.jwt_secret, algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            raise ValidationError("refresh_token 已过期")
        except jwt.InvalidTokenError:
            raise ValidationError("无效的 refresh_token")

        if payload.get("type") != "refresh":
            raise ValidationError("非 refresh_token")

        user = await self.get_user(payload["sub"])
        new_access = self._sign_token(user)
        return {
            "access_token": new_access,
            "token_type": "bearer",
            "expires_in": 86400,
        }
