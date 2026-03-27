"""
user_profile 路由
─────────────────
路径前缀：/api/v1
认证端点 3 个：短信发送、短信验证、Token 刷新
用户端点 2 个：查看/更新我的信息
学生档案 2 个：查看/更新学生档案
家长绑定 2 个：发起绑定、绑定列表
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis

from database import get_db
from deps import get_jwt_manager, get_current_user
from shared.exceptions import UnauthorizedError
from shared.schemas import ok
from shared.security import JWTManager, TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from user_profile.schemas import (
    GuardianBindRequest,
    GuardianBindingOut,
    RefreshTokenRequest,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
    StudentProfileOut,
    StudentProfileUpdateRequest,
    TokenResponse,
    UserOut,
    UserUpdateRequest,
    WxLoginRequest,
)
from user_profile.service import UserService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["user-profile"])


# ── 内部依赖 ──────────────────────────────────────────

_redis_instance: Redis | None = None


def set_redis(redis: Redis) -> None:
    """由 main.py lifespan 调用，注入 Redis 连接"""
    global _redis_instance
    _redis_instance = redis


def get_redis() -> Redis:
    if _redis_instance is None:
        raise RuntimeError("Redis not initialized — call set_redis() in lifespan")
    return _redis_instance


def _build_service(
    db: AsyncSession = Depends(get_db),
    jwt_mgr: JWTManager = Depends(get_jwt_manager),
) -> UserService:
    return UserService(db=db, jwt_mgr=jwt_mgr)


# 类型别名
Svc = Annotated[UserService, Depends(_build_service)]
RedisConn = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 认证
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/auth/sms/send")
async def send_sms_code(body: SmsSendRequest, svc: Svc, redis: RedisConn):
    """
    发送短信验证码
    - 同一手机号 60s 内不能重复发送（Redis 限流）
    - 验证码 5 分钟有效
    """
    ttl = await svc.send_sms_code(phone=body.phone, redis=redis)
    return ok(SmsSendResponse(expire_seconds=ttl).model_dump())


@router.post("/auth/sms/verify")
async def verify_sms_code(body: SmsVerifyRequest, svc: Svc, redis: RedisConn):
    """
    短信验证码登录
    - 验证通过后自动注册（首次）或登录（已有用户）
    - 返回 access_token + refresh_token
    """
    tokens = await svc.verify_sms_code(
        phone=body.phone, code=body.code, redis=redis
    )
    return ok(TokenResponse(**tokens).model_dump())


@router.post("/auth/wx/login")
async def wx_login(body: WxLoginRequest, svc: Svc):
    """
    微信登录（小程序 / 公众号）
    - code 换 session_key + openid
    - 自动注册或登录
    - 返回 access_token + refresh_token
    """
    tokens = await svc.wx_login(code=body.code, provider=body.provider)
    return ok(TokenResponse(**tokens).model_dump())


@router.post("/auth/token/refresh")
async def refresh_token(body: RefreshTokenRequest, svc: Svc, redis: RedisConn):
    """
    刷新 access_token
    - 验证 refresh_token 有效性
    - 检查是否在黑名单中
    - 签发新的 token 对
    """
    try:
        payload = svc.jwt.get_payload(body.refresh_token)
    except Exception:
        raise UnauthorizedError("invalid refresh token")

    # 检查黑名单
    blacklisted = await redis.get(f"token:blacklist:{payload.jti}")
    if blacklisted:
        raise UnauthorizedError("token has been revoked")

    user = await svc.get_user(payload.sub)
    tokens = svc.create_tokens(user)
    return ok(TokenResponse(**tokens).model_dump())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 用户信息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/users/me")
async def get_me(user: CurrentUser, svc: Svc):
    """获取当前用户基本信息"""
    u = await svc.get_user(user.sub)
    return ok(UserOut.model_validate(u).model_dump())


@router.patch("/users/me")
async def update_me(body: UserUpdateRequest, user: CurrentUser, svc: Svc):
    """更新当前用户信息（昵称、头像等）"""
    u = await svc.update_user(
        user_id=user.sub, **body.model_dump(exclude_unset=True)
    )
    return ok(UserOut.model_validate(u).model_dump())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 学生档案
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/users/me/student-profile")
async def get_student_profile(user: CurrentUser, svc: Svc):
    """获取学生档案（不存在则自动创建空档案）"""
    profile = await svc.get_or_create_student_profile(user.sub)
    return ok(StudentProfileOut.model_validate(profile).model_dump())


@router.patch("/users/me/student-profile")
async def update_student_profile(
    body: StudentProfileUpdateRequest, user: CurrentUser, svc: Svc
):
    """更新学生档案（年级、学校、学习偏好等）"""
    profile = await svc.update_student_profile(
        user_id=user.sub, **body.model_dump(exclude_unset=True)
    )
    return ok(StudentProfileOut.model_validate(profile).model_dump())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 家长绑定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/users/me/guardian-bindings")
async def create_guardian_binding(
    body: GuardianBindRequest, user: CurrentUser, svc: Svc
):
    """
    家长发起绑定学生
    - 通过学生手机号查找学生
    - 创建 pending 绑定记录
    """
    binding = await svc.bind_guardian(
        guardian_id=user.sub,
        student_phone=body.student_phone,
        relationship=body.relationship_type,
    )
    return ok(GuardianBindingOut.model_validate(binding).model_dump())


@router.get("/users/me/guardian-bindings")
async def list_guardian_bindings(user: CurrentUser, svc: Svc):
    """获取当前用户的家长绑定列表"""
    bindings = await svc.list_guardian_bindings(user_id=user.sub)
    return ok([GuardianBindingOut.model_validate(b).model_dump() for b in bindings])
