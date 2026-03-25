# 安全基线

> 父文档：[README.md](./README.md)

---

## 1. 概述

定义 zhiqu-classroom 平台的安全基准规范，覆盖认证鉴权、数据安全、传输安全、依赖安全和运维安全。MVP 阶段以实用为主，不过度设计，但为后续安全合规留好接口。

## 2. 认证与鉴权

### 2.1 JWT 认证

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 算法 | HS256（MVP）→ RS256（正式） | |
| Access Token 有效期 | 2 小时 | |
| Refresh Token 有效期 | 7 天 | |
| 签名密钥 | 环境变量 `JWT_SECRET` | 至少 32 字节随机值 |
| 载荷内容 | user_id, role, exp, iat | 不包含敏感信息 |

### Token 刷新流程

```
Access Token 过期
       │
       ▼
  POST /api/v1/auth/token/refresh
       │  携带 Refresh Token
       ▼
  验证 Refresh Token 有效性
       │
       ├── 有效 → 签发新 Access Token + 新 Refresh Token（轮换）
       └── 无效 → 401，要求重新登录
```

**Refresh Token 轮换**：每次刷新时旧 Refresh Token 立即失效，防止重放。

### 2.2 角色与权限

| 角色 | 标识 | 权限范围 |
|------|------|----------|
| 超级管理员 | `super_admin` | 全部权限 |
| 管理员 | `admin` | 用户管理、内容管理、LLM 管理、系统配置 |
| 教师 | `teacher` | 班级管理、任务管理、学习数据查看 |
| 学生 | `student` | 完成任务、查看自己的学习数据 |
| 家长 | `guardian` | 查看绑定学生的学习数据 |

### 权限检查

```python
# services/shared/auth/deps.py

from fastapi import Depends, HTTPException

def require_roles(*roles: str):
    """角色权限装饰器"""
    async def checker(current_user = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail={"code": 40101, "message": "权限不足"},
            )
        return current_user
    return checker


# 使用示例
@router.post("/tasks")
async def create_task(
    payload: TaskCreate,
    user = Depends(require_roles("admin", "teacher")),
):
    ...
```

## 3. 数据安全

### 3.1 敏感数据加密

| 数据类型 | 存储方式 | 说明 |
|----------|----------|------|
| 用户密码 | bcrypt hash（cost=12） | 不可逆 |
| LLM API Key | AES-256-GCM 加密 | 密钥从环境变量 `ENCRYPTION_KEY` 读取 |
| Refresh Token | SHA256 hash | 数据库只存哈希，不存明文 |
| 手机号 | 明文（MVP）→ 加密（正式） | 需要检索时使用密文索引 |

### 加密工具

```python
# services/shared/crypto.py

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class Encryptor:
    def __init__(self):
        key_hex = os.environ["ENCRYPTION_KEY"]  # 64 char hex = 32 bytes
        self._key = bytes.fromhex(key_hex)

    def encrypt(self, plaintext: str) -> str:
        """AES-256-GCM 加密，返回 base64(nonce + ciphertext + tag)"""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        """解密"""
        data = base64.b64decode(ciphertext_b64)
        nonce, ct = data[:12], data[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ct, None).decode()
```

### 3.2 数据脱敏

应用层日志和 API 响应中的敏感数据脱敏规则（详见 [logging/ 文档](../logging/README.md)）：

| 数据类型 | 脱敏规则 | 示例 |
|----------|----------|------|
| 手机号 | 保留前 3 后 4 | `138****1234` |
| API Key | 保留前 6 后 4 | `sk-abc1****5678` |
| Token | 保留前 6 后 4 | `eyJhbG****XVCJ` |
| Password / Secret | 全替换 | `***` |

### 3.3 软删除

所有业务表使用 `deleted_at` (nullable TIMESTAMP) 实现软删除：

- `deleted_at IS NULL` → 正常记录
- `deleted_at IS NOT NULL` → 已删除
- 查询默认过滤已删除记录（SQLAlchemy mixin 实现）
- 物理删除需走审计流程，仅 super_admin 可执行

## 4. 传输安全

### 4.1 HTTPS

| 环境 | 方式 |
|------|------|
| 生产 | Nginx / Caddy 反向代理，TLS 1.2+ |
| 开发 | HTTP 可用（本地开发） |

### 4.2 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 白名单，不用 ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)
```

### 4.3 请求安全头

```python
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

## 5. 输入校验

### 5.1 通用规则

| 规则 | 说明 |
|------|------|
| 字符串长度限制 | 所有字符串字段设定 `max_length` |
| SQL 注入防护 | 全量使用 SQLAlchemy ORM / 参数化查询 |
| XSS 防护 | 富文本入库前过滤（bleach / html-sanitizer） |
| 文件上传限制 | 类型白名单 + 大小限制（教材 50MB，图片 10MB） |
| 请求体大小 | 默认 10MB 上限 |

### 5.2 Pydantic 校验示例

```python
from pydantic import BaseModel, Field, validator

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    task_type: str = Field(...)
    grade_range: str = Field(...)

    @validator("task_type")
    def validate_task_type(cls, v):
        allowed = {"after_class", "review", "assessment"}
        if v not in allowed:
            raise ValueError(f"task_type 必须是 {allowed} 之一")
        return v
```

## 6. 限流

### 6.1 策略

| 端点类型 | 限制 | 说明 |
|----------|------|------|
| 登录/短信 | 5 次/分钟/IP | 防暴力破解 |
| 普通 API | 60 次/分钟/用户 | 防滥用 |
| LLM 调用 | 10 次/分钟/用户 | 保护 LLM 成本 |
| 文件上传 | 10 次/小时/用户 | 防存储滥用 |
| 管理 API | 120 次/分钟/用户 | 管理操作宽松限制 |

### 6.2 实现

基于 Redis 滑动窗口：

```python
# services/shared/rate_limiter.py

class RateLimiter:
    async def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """滑动窗口限流，返回 True = 允许"""
        now = time.time()
        pipe = self.redis.pipeline()

        # 移除窗口外的记录
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        # 添加当前请求
        pipe.zadd(key, {str(now): now})
        # 计数
        pipe.zcard(key)
        # 设置 key 过期（防止泄漏）
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        count = results[2]

        return count <= limit
```

超限时返回：

```json
{
  "code": 40003,
  "message": "请求过于频繁，请稍后再试",
  "data": {"retry_after_seconds": 30}
}
```

HTTP 响应头：

```
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1711353600
```

## 7. 依赖安全

| 实践 | 工具 | 频率 |
|------|------|------|
| Python 依赖漏洞扫描 | `pip-audit` / `safety` | 每次 CI + 每周定时 |
| Docker 镜像扫描 | `trivy` | 每次构建 |
| 基础镜像更新 | `python:3.12-slim` 系列 | 每月检查 |
| 依赖锁定 | `poetry.lock` / `requirements.lock` | 始终锁定版本 |

### CI 集成

```yaml
# .github/workflows/security.yml
- name: Audit Python deps
  run: pip-audit -r requirements.lock --strict

- name: Scan Docker image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: zhiqu-classroom/content-engine:${{ github.sha }}
    severity: CRITICAL,HIGH
```

## 8. 运维安全

| 实践 | 说明 |
|------|------|
| 环境变量管理 | 敏感配置走 `.env`（Git 忽略）或 Secret Manager |
| 数据库访问 | 应用账户最小权限（无 DROP/TRUNCATE） |
| SSH 访问 | 禁止密码登录，仅 SSH Key |
| 容器运行 | 非 root 用户运行应用 |
| 日志脱敏 | 不记录明文密码/密钥（详见日志规范） |

### Dockerfile 安全实践

```dockerfile
# 非 root 运行
RUN addgroup --system app && adduser --system --ingroup app app
USER app

# 最小化镜像
FROM python:3.12-slim
# 不安装推荐包
RUN apt-get update && apt-get install -y --no-install-recommends ...
```
