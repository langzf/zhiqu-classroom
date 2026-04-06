"""接口层 Schema 基类 — ORM 兼容"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """ORM 兼容基类"""
    model_config = ConfigDict(from_attributes=True)


class IdTimestampSchema(OrmBase):
    """带 id + 时间戳的基础响应"""
    id: UUID
    created_at: datetime
    updated_at: datetime
