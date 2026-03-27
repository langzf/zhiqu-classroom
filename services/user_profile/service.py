"""user_profile 业务逻辑"""

import random
import string
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ConflictError, NotFoundError, UnauthorizedError
from shared.security import JWTManager
from user_profile.models import (
    GuardianBinding,
    StudentProfile,
    User,
    UserOAuthBinding,
)
from shared.base_model import generate_uuid7

logger = structlog.get_logger()


class UserService:
    """用户相关业务逻辑"""

    def __init__(self, db: AsyncSession, jwt_mgr: JWTManager):
        self.db = db
        self.jwt = jwt_mgr

    # ── SMS 验证码 ────────────────────────────────────

    @staticmethod
    def generate_code(length: int = 6) -> str:
        return "".join(random.choices(string.digits, k=length))

    async def send_sms_code(self, phone: str, redis) -> int:
        """发送短信验证码，返回 TTL 秒数"""
        # TODO: 频率限制检查（1分钟内不可重发）
        code = self.generate_code()
        ttl = 300  # 5 分钟
        key = f"sms:code:{phone}"

        await redis.setex(key, ttl, code)
        logger.info("sms_code_sent", phone=phone[-4:])

        # TODO: 对接实际 SMS 供应商（mock 模式下直接 print）
        logger.info("sms_code_mock", code=code, phone=phone[-4:])
        return ttl

    async def verify_sms_code(self, phone: str, code: str, redis) -> dict:
        """验证短信验证码，返回 token 对"""
        key = f"sms:code:{phone}"
        stored = await redis.get(key)

        if not stored or stored != code:
            raise UnauthorizedError("invalid or expired code")

        await redis.delete(key)

        # 查找或创建用户
        user = await self._get_or_create_user_by_phone(phone)
        return self._issue_tokens(user)

    async def _get_or_create_user_by_phone(self, phone: str) -> User:
        stmt = select(User).where(
            User.phone == phone, User.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=generate_uuid7(),
                phone=phone,
                nickname=f"用户{phone[-4:]}",
                role="student",
            )
            self.db.add(user)
            await self.db.flush()
            logger.info("user_created", user_id=str(user.id), phone=phone[-4:])

        user.last_login_at = datetime.now(timezone.utc)
        return user

    def _issue_tokens(self, user: User) -> dict:
        access = self.jwt.create_access_token(str(user.id), user.role)
        refresh = self.jwt.create_refresh_token(str(user.id), user.role)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 min
        }

    def create_tokens(self, user: User) -> dict:
        """公开方法 — 给 router 的 token 刷新场景调用"""
        return self._issue_tokens(user)

    # ── 微信登录 ──────────────────────────────────────

    async def wx_login(self, code: str, provider: str = "wechat_mp") -> dict:
        """
        微信登录
        - code 换取 openid / session_key
        - 查找或创建用户 + OAuth 绑定
        - 返回 token 对
        """
        # TODO: 调用微信 API — code2Session (小程序) / OAuth2 (公众号)
        # 以下为 mock 实现，实际接入时替换
        open_id = f"mock_openid_{code[:8]}"
        union_id = None  # 未关联开放平台时为空

        # 查找已有 OAuth 绑定
        stmt = select(UserOAuthBinding).where(
            UserOAuthBinding.provider == provider,
            UserOAuthBinding.open_id == open_id,
        )
        result = await self.db.execute(stmt)
        binding = result.scalar_one_or_none()

        if binding:
            user = await self.get_user(str(binding.user_id))
        else:
            # 新用户
            user = User(
                id=generate_uuid7(),
                nickname="微信用户",
                role="student",
            )
            self.db.add(user)
            await self.db.flush()

            oauth = UserOAuthBinding(
                user_id=user.id,
                provider=provider,
                open_id=open_id,
                union_id=union_id,
            )
            self.db.add(oauth)
            await self.db.flush()
            logger.info(
                "wx_user_created",
                user_id=str(user.id),
                provider=provider,
            )

        user.last_login_at = datetime.now(timezone.utc)
        return self._issue_tokens(user)

    # ── 用户信息 ──────────────────────────────────────

    async def get_user(self, user_id: str) -> User:
        stmt = select(User).where(
            User.id == user_id, User.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("user", user_id)
        return user

    async def update_user(self, user_id: str, **kwargs) -> User:
        user = await self.get_user(user_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(user, k):
                setattr(user, k, v)
        await self.db.flush()
        return user

    # ── 学生档案 ──────────────────────────────────────

    async def get_or_create_student_profile(self, user_id: str) -> StudentProfile:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = StudentProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
        return profile

    async def update_student_profile(self, user_id: str, **kwargs) -> StudentProfile:
        profile = await self.get_or_create_student_profile(user_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(profile, k):
                setattr(profile, k, v)
        await self.db.flush()
        return profile

    # ── 家长绑定 ──────────────────────────────────────

    async def bind_guardian(
        self, guardian_id: str, student_phone: str, relationship_type: str = "other"
    ) -> GuardianBinding:
        # 查找学生
        stmt = select(User).where(
            User.phone == student_phone,
            User.role == "student",
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        student = result.scalar_one_or_none()
        if not student:
            raise NotFoundError("student", student_phone)

        # 检查重复绑定
        stmt = select(GuardianBinding).where(
            GuardianBinding.guardian_id == guardian_id,
            GuardianBinding.student_id == student.id,
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictError("already bound")

        binding = GuardianBinding(
            guardian_id=guardian_id,
            student_id=student.id,
            relationship_type=relationship_type,
            bind_status="pending",
        )
        self.db.add(binding)
        await self.db.flush()
        logger.info(
            "guardian_bound",
            guardian_id=guardian_id,
            student_id=str(student.id),
        )
        return binding

    async def list_guardian_bindings(self, user_id: str) -> list[GuardianBinding]:
        """列出与当前用户相关的家长绑定（作为家长或学生）"""
        stmt = select(GuardianBinding).where(
            (GuardianBinding.guardian_id == user_id)
            | (GuardianBinding.student_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
