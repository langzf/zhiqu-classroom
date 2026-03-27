"""JWT 工具 — 签发、验证、刷新"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str  # user_id
    role: str  # student / guardian / admin
    exp: datetime
    iat: datetime
    jti: str  # token id for blacklist


class JWTManager:
    """JWT 管理器"""

    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def create_access_token(
        self,
        user_id: str,
        role: str,
        expires_minutes: int = 30,
        extra: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        from uuid6 import uuid7

        payload = {
            "sub": user_id,
            "role": role,
            "exp": now + timedelta(minutes=expires_minutes),
            "iat": now,
            "jti": str(uuid7()),
        }
        if extra:
            payload.update(extra)
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        role: str,
        expires_days: int = 7,
    ) -> str:
        now = datetime.now(timezone.utc)
        from uuid6 import uuid7

        payload = {
            "sub": user_id,
            "role": role,
            "exp": now + timedelta(days=expires_days),
            "iat": now,
            "jti": str(uuid7()),
            "type": "refresh",
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """解码并验证 token，过期或无效会抛异常"""
        return jwt.decode(token, self.secret, algorithms=[self.algorithm])

    def get_payload(self, token: str) -> TokenPayload:
        data = self.decode_token(token)
        return TokenPayload(**data)
