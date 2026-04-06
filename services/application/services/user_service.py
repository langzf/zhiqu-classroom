"""
用户服务
─────────────────────
用户注册/登录、个人信息、家长绑定。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt
import structlog
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from shared.base_model import generate_uuid7
from shared.exceptions import NotFoundError, ValidationError

from infrastructure.persistence.models.user import GuardianBinding, User

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

    async def login(self, phone: str, *, require_admin: bool = False) -> dict:
        """
        手机号登录（MVP 跳过验证码校验，直接签发 token）。

        Args:
            phone: 手机号
            require_admin: 若为 True，仅允许 admin 角色登录（管理后台专用）；
                           若为 False（默认），用户不存在时自动注册为 student。
        """
        user = await self._get_by_phone(phone)

        if require_admin:
            # 管理后台登录：用户必须存在且为 admin
            # 统一错误消息，避免泄漏手机号是否已注册
            print(f"[DEBUG] admin_login_check: user={user}, user.role={user.role if user else None}, phone={phone}")
            if not user or user.role != "admin":
                print(f"[DEBUG] Rejecting: user={bool(user)}, role={user.role if user else 'N/A'}")
                raise ValidationError("该账号无管理后台访问权限")
        else:
            # 学生端登录：不存在则自动注册
            if not user:
                user = User(
                    phone=phone,
                    nickname=f"用户{phone[-4:]}",
                    role="student",
                )
                self.db.add(user)
                await self.db.flush()
                await self.db.refresh(user)

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

    # ── Admin 管理 ─────────────────────────────────────

    async def list_users(
        self,
        role: str | None = None,
        is_active: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        # 兼容旧调用
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[User], int]:
        """Admin: 分页列出用户。"""
        q = select(User).where(User.deleted_at.is_(None))
        count_q = (
            select(sa_func.count()).select_from(User).where(User.deleted_at.is_(None))
        )

        if role:
            q = q.where(User.role == role)
            count_q = count_q.where(User.role == role)
        if is_active is not None:
            q = q.where(User.is_active == is_active)
            count_q = count_q.where(User.is_active == is_active)
        if keyword:
            like = f"%{keyword}%"
            q = q.where((User.nickname.ilike(like)) | (User.phone.ilike(like)))
            count_q = count_q.where(
                (User.nickname.ilike(like)) | (User.phone.ilike(like))
            )

        total = (await self.db.execute(count_q)).scalar() or 0
        # 支持 page/page_size 或 limit/offset 两种调用方式
        if limit is not None or offset is not None:
            _offset = offset or 0
            _limit = limit or 20
        else:
            _offset = (page - 1) * page_size
            _limit = page_size
        q = q.order_by(User.created_at.desc()).offset(_offset).limit(_limit)
        result = await self.db.execute(q)
        users = list(result.scalars().all())
        return users, total

    async def admin_get_user(self, user_id: UUID) -> User:
        """Admin: 获取用户详情。"""
        user = await self.db.get(User, user_id)
        if not user or user.deleted_at:
            raise NotFoundError("用户不存在")
        return user

    async def admin_update_user(self, user_id: UUID, body=None, **kwargs) -> User:
        """Admin: 更新用户字段（role, is_active, nickname 等）。
        
        支持两种调用方式:
        - admin_update_user(user_id, body)  — body 为 Pydantic model
        - admin_update_user(user_id, role=..., is_active=...)  — 关键字参数
        """
        user = await self.db.get(User, user_id)
        if not user or user.deleted_at:
            raise NotFoundError("用户不存在")
        
        # 如果传了 Pydantic body，解包为 dict
        if body is not None and hasattr(body, 'model_dump'):
            updates = body.model_dump(exclude_unset=True)
        elif body is not None and isinstance(body, dict):
            updates = body
        else:
            updates = kwargs
        
        for k, v in updates.items():
            if v is not None and hasattr(user, k):
                setattr(user, k, v)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # ── 用户 CRUD ─────────────────────────────────────

    async def get_user(self, user_id: str) -> User:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        return user

    async def update_user(self, user_id: str, body=None, **kwargs) -> User:
        """更新用户信息。支持 Pydantic body 或关键字参数。"""
        user = await self.get_user(user_id)
        if body is not None and hasattr(body, 'model_dump'):
            updates = body.model_dump(exclude_unset=True)
        elif body is not None and isinstance(body, dict):
            updates = body
        else:
            updates = kwargs
        for k, v in updates.items():
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

    # ── Token 签发 ────────────────────────────────────

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

    # ── 内部方法 ──────────────────────────────────────

    async def _get_by_phone(self, phone: str) -> Optional[User]:
        stmt = select(User).where(User.phone == phone, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
