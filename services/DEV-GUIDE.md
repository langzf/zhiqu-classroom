# 后端开发规范 (services)

> 适用于 `services/` 下所有 Python 后端模块  
> 技术栈：Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL 16 · Redis 7  
> 最后更新：2026-03-25

---

## 目录

1. [项目结构规范](#1-项目结构规范)
2. [Python 编码规范](#2-python-编码规范)
3. [FastAPI 路由规范](#3-fastapi-路由规范)
4. [数据库规范](#4-数据库规范)
5. [日志规范](#5-日志规范)
6. [错误处理规范](#6-错误处理规范)
7. [测试规范](#7-测试规范)
8. [Git 工作流](#8-git-工作流)
9. [环境与依赖管理](#9-环境与依赖管理)
10. [安全规范](#10-安全规范)

---

## 1. 项目结构规范

### 1.1 单服务模块结构

MVP 阶段所有模块在同一进程中运行，但保持独立的 package 边界：

```
services/
├── shared/                     # 公共库
│   ├── config.py               #   配置管理（Pydantic Settings）
│   ├── database.py             #   数据库连接 / Session
│   ├── redis.py                #   Redis 连接
│   ├── auth.py                 #   JWT 认证
│   ├── logging.py              #   structlog 初始化
│   ├── middleware.py            #   通用中间件
│   ├── schemas.py              #   公共响应 Schema
│   ├── exceptions.py           #   统一异常类
│   └── utils.py                #   工具函数
├── api-gateway/
│   ├── main.py                 #   MVP 单体入口
│   ├── routers/                #   路由聚合
│   └── README.md
├── content-engine/
│   ├── router.py               #   路由定义
│   ├── service.py              #   业务逻辑层
│   ├── models.py               #   SQLAlchemy ORM 模型
│   ├── schemas.py              #   Pydantic 请求/响应模型
│   ├── repository.py           #   数据访问层
│   ├── events.py               #   事件发布/消费
│   └── tests/                  #   单元 + 集成测试
├── ...（其他服务模块同上）
├── CONTRACTS.md                #   服务契约
├── DEV-GUIDE.md                #   本文件
└── README.md
```

### 1.2 模块内分层

每个服务模块严格分为四层：

| 层 | 文件 | 职责 | 允许依赖 |
|----|------|------|----------|
| **路由层** | `router.py` | 接收请求、参数校验、调用 Service | schemas, service |
| **服务层** | `service.py` | 业务逻辑编排、事务控制 | repository, events, shared |
| **数据层** | `repository.py` | 数据库 CRUD、查询封装 | models, database |
| **模型层** | `models.py` / `schemas.py` | ORM 模型 + Pydantic DTO | shared |

> ⚠️ **禁止跳层调用**：Router 不得直接操作 Repository，Service 不得直接操作 Session。

### 1.3 命名约定

| 类别 | 规范 | 示例 |
|------|------|------|
| 文件名 | 小写下划线 | `textbook_parser.py` |
| 类名 | PascalCase | `TextbookService` |
| 函数名 | snake_case | `parse_textbook()` |
| 常量 | UPPER_SNAKE | `MAX_RETRY_COUNT = 5` |
| 路由路径 | 短横线分隔 | `/api/v1/knowledge-points` |
| 数据库表 | 小写下划线 | `knowledge_points` |
| 环境变量 | UPPER_SNAKE | `DB_PASSWORD` |

---

## 2. Python 编码规范

### 2.1 基础规范

- **Python 版本**：3.12+，充分使用 type hints
- **格式化**：Ruff（替代 Black + isort + Flake8）
- **类型检查**：mypy（strict mode）
- **行宽**：120 字符
- **缩进**：4 空格

```toml
# pyproject.toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
```

### 2.2 类型标注

```python
# ✅ 所有公开函数必须有完整类型标注
async def get_textbook(textbook_id: UUID, db: AsyncSession) -> TextbookDetail:
    ...

# ✅ 使用 Python 3.12 新语法
type TextbookId = UUID
type ChapterTree = list[ChapterNode]

# ❌ 不要使用 Any，除非确有必要并加注释
def process(data: Any) -> None:  # type: ignore[misc] — 第三方库未提供类型
    ...
```

### 2.3 异步编程

```python
# ✅ IO 操作全部使用 async/await
async def create_textbook(data: TextbookCreate, db: AsyncSession) -> Textbook:
    textbook = Textbook(**data.model_dump())
    db.add(textbook)
    await db.flush()
    return textbook

# ✅ 并发无依赖的 IO 操作
chapters, kp_count = await asyncio.gather(
    chapter_repo.list_by_textbook(textbook_id),
    kp_repo.count_by_textbook(textbook_id),
)

# ❌ 不要在 async 函数中使用同步阻塞调用
# 如必须调用同步库，使用 run_in_executor
result = await asyncio.get_event_loop().run_in_executor(
    None, sync_heavy_function, arg1
)
```

### 2.4 Import 排序

```python
# 标准库
import asyncio
from uuid import UUID

# 第三方库
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 本地共享
from shared.auth import get_current_user
from shared.database import get_db

# 当前模块
from .schemas import TextbookCreate, TextbookDetail
from .service import TextbookService
```

---

## 3. FastAPI 路由规范

### 3.1 路径设计

```python
router = APIRouter(prefix="/api/v1/textbooks", tags=["textbooks"])

# ✅ 资源用复数名词
@router.get("/")                              # 列表
@router.post("/")                             # 创建
@router.get("/{textbook_id}")                 # 详情
@router.put("/{textbook_id}")                 # 全量更新
@router.patch("/{textbook_id}")               # 部分更新
@router.delete("/{textbook_id}")              # 删除

# ✅ 嵌套资源最多两级
@router.get("/{textbook_id}/chapters")        # 获取章节
@router.get("/{textbook_id}/chapters/{chapter_id}")

# ✅ 动作用动词子路径
@router.post("/{textbook_id}/parse")          # 触发解析
@router.post("/{textbook_id}/retry")          # 重试

# ❌ 不要超过两级嵌套
# /textbooks/{id}/chapters/{cid}/knowledge-points/{kpid}/exercises
```

### 3.2 统一响应格式

```python
from shared.schemas import ApiResponse, PagedResponse

@router.get("/{textbook_id}", response_model=ApiResponse[TextbookDetail])
async def get_textbook(
    textbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = TextbookService(db)
    textbook = await svc.get_by_id(textbook_id)
    return ApiResponse(data=textbook)

# 分页响应
@router.get("/", response_model=PagedResponse[TextbookSummary])
async def list_textbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ...
):
    items, total = await svc.list_paged(page, page_size)
    return PagedResponse(data=items, total=total, page=page, page_size=page_size)
```

### 3.3 依赖注入

```python
# ✅ 使用 Depends 注入公共依赖
async def get_textbook_service(db: AsyncSession = Depends(get_db)) -> TextbookService:
    return TextbookService(db)

@router.post("/")
async def create(
    data: TextbookCreate,
    current_user: User = Depends(require_role("admin")),  # 角色校验
    svc: TextbookService = Depends(get_textbook_service),
):
    return ApiResponse(data=await svc.create(data, current_user.id))
```

### 3.4 请求校验

```python
from pydantic import BaseModel, Field, field_validator

class TextbookCreate(BaseModel):
    """创建教材请求"""
    title: str = Field(..., min_length=1, max_length=200, description="教材标题")
    subject: Subject                          # 枚举校验
    grade_start: Grade
    grade_end: Grade
    
    @field_validator("grade_end")
    @classmethod
    def grade_range_valid(cls, v: Grade, info) -> Grade:
        if v.value < info.data.get("grade_start", Grade.GRADE_1).value:
            raise ValueError("grade_end must >= grade_start")
        return v

    model_config = ConfigDict(
        str_strip_whitespace=True,  # 自动去首尾空格
    )
```

---

## 4. 数据库规范

### 4.1 ORM 模型

```python
from sqlalchemy import String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from uuid import UUID

class Base(DeclarativeBase):
    """所有模型基类"""
    pass

class TimestampMixin:
    """时间戳 Mixin"""
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), onupdate=text("now()"), nullable=False
    )

class SoftDeleteMixin:
    """软删除 Mixin"""
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)

class Textbook(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "textbooks"
    __table_args__ = {"schema": "content"}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False
    )
```

### 4.2 数据库迁移

```bash
# 使用 Alembic 管理迁移
alembic revision --autogenerate -m "add textbooks table"
alembic upgrade head
alembic downgrade -1
```

**迁移规则：**

- 每个迁移只做一件事
- 迁移文件必须可逆（提供 `downgrade`）
- 禁止在迁移中写入业务数据（用 seed 脚本代替）
- 线上执行前必须在 staging 验证

### 4.3 查询规范

```python
# ✅ 使用 select() 语法（SQLAlchemy 2.0 风格）
from sqlalchemy import select, func

stmt = (
    select(Textbook)
    .where(Textbook.deleted_at.is_(None))
    .where(Textbook.subject == subject)
    .order_by(Textbook.created_at.desc())
    .offset(offset)
    .limit(limit)
)
result = await db.execute(stmt)
textbooks = result.scalars().all()

# ✅ 批量操作使用 executemany
await db.execute(
    insert(KnowledgePoint),
    [kp.model_dump() for kp in knowledge_points],
)

# ❌ 不要在循环中执行单条 SQL
for kp in knowledge_points:
    db.add(KnowledgePoint(**kp.model_dump()))  # N+1 问题
    await db.flush()
```

### 4.4 索引命名

```
idx_{table}_{column}                # 普通索引
uq_{table}_{column}                 # 唯一索引
idx_{table}_{col1}_{col2}           # 复合索引
```

### 4.5 Schema 隔离

| Schema | 归属服务 | 说明 |
|--------|----------|------|
| `user_profile` | user-profile | 用户、学生档案、监护人绑定 |
| `content` | content-engine | 教材、章节、知识点、向量 |
| `media` | media-generation | 互动资源、生成任务 |
| `learning` | learning-orchestrator | 学习任务、作答记录 |
| `analytics` | analytics-reporting | 统计快照、报表 |
| `notification` | notification | 通知记录、模板 |
| `conversation` | ai-tutor | 会话、消息、反馈 |
| `llm_ops` | shared (LLM Gateway) | 模型配置、调用日志、路由规则 |
| `platform` | shared | 系统配置、审计日志、异步任务 |

> ⚠️ **禁止跨 Schema 直连**。跨服务数据通过内部 API 或事件投影获取。

---

## 5. 日志规范

> 完整日志设计见 [docs/logging-design.md](../docs/logging-design.md)，此处摘录开发要点。

### 5.1 日志库

统一使用 **structlog**，禁止直接使用 `print()` 或 `logging.getLogger()`。

```python
import structlog

logger = structlog.get_logger("content_engine.textbook_parser")
```

### 5.2 结构化参数

```python
# ✅ 使用关键字参数，不要拼接字符串
logger.info("教材解析完成",
    textbook_id=str(textbook_id),
    chapters=chapter_count,
    duration_ms=elapsed,
)

# ❌ 绝对不要
logger.info(f"教材 {textbook_id} 解析完成，共 {chapter_count} 章，耗时 {elapsed}ms")
```

### 5.3 级别使用

| 级别 | 场景 | 关键规则 |
|------|------|----------|
| DEBUG | 循环内细节、变量值 | 生产默认关闭 |
| INFO | 请求入口/出口、状态变更 | **每个请求至少 2 条**（入口+出口） |
| WARNING | 降级、重试、接近阈值 | 可自愈的异常 |
| ERROR | 不可恢复的业务异常 | **必须附带 `exc_info=True`** |
| CRITICAL | 系统级致命错误 | 数据库连接耗尽、LLM 全部不可用 |

### 5.4 Logger 命名

```
{service}.{module}          → content_engine.textbook_parser
llm.call                    → LLM 调用（统一命名空间）
task.{task_name}            → 异步任务
http.access                 → HTTP 访问日志
audit                       → 审计日志
```

### 5.5 敏感字段脱敏

日志中禁止出现以下明文：手机号、JWT Token、密码、身份证号。structlog 处理链中自动脱敏：

```python
# 自动脱敏处理器
def sanitize_processor(logger, method_name, event_dict):
    for key in ("phone", "token", "password", "id_card"):
        if key in event_dict:
            event_dict[key] = mask(event_dict[key])
    return event_dict
```

---

## 6. 错误处理规范

### 6.1 统一异常类

```python
# shared/exceptions.py
class AppError(Exception):
    """业务异常基类"""
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=404001,
            message=f"{resource} not found: {resource_id}",
            status_code=404,
        )

class ForbiddenError(AppError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(code=403001, message=message, status_code=403)

class RateLimitError(AppError):
    def __init__(self, retry_after: int = 60):
        super().__init__(code=429001, message="Too many requests", status_code=429)
        self.retry_after = retry_after
```

### 6.2 全局异常处理器

```python
# 在 main.py 中注册
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "request_id": request.state.request_id,
        },
    )
```

### 6.3 错误码规范

```
格式：{HTTP状态码}{模块编号}{序号}

模块编号：
  00 = 通用
  01 = 认证/用户
  02 = 教材/知识点
  03 = 内容生成
  04 = AI 辅导
  05 = 学习任务
  06 = 统计报表
  07 = 管理后台

示例：
  400001 = 通用参数错误
  401011 = 验证码过期
  401012 = 验证码错误
  404021 = 教材不存在
  429001 = 频率限制
```

---

## 7. 测试规范

### 7.1 测试结构

```
services/{module}/tests/
├── conftest.py              # 测试 fixtures
├── test_router.py           # 路由层（集成测试）
├── test_service.py          # 服务层（单元测试）
├── test_repository.py       # 数据层（需要 DB）
└── factories.py             # 测试数据工厂
```

### 7.2 测试工具

| 工具 | 用途 |
|------|------|
| **pytest** | 测试框架 |
| **pytest-asyncio** | 异步测试支持 |
| **httpx** | FastAPI TestClient (async) |
| **factory-boy** | 测试数据工厂 |
| **pytest-cov** | 覆盖率统计 |

### 7.3 测试规则

```python
# ✅ 测试函数命名：test_{method}_{scenario}_{expected}
async def test_create_textbook_valid_input_returns_201():
    ...

async def test_create_textbook_duplicate_title_returns_409():
    ...

# ✅ 使用 fixtures 管理测试数据
@pytest.fixture
async def sample_textbook(db: AsyncSession) -> Textbook:
    return await TextbookFactory.create(db, subject="math")

# ✅ 每个测试独立，不依赖执行顺序
# ✅ 集成测试使用事务回滚而非清表
```

### 7.4 覆盖率要求

| 层 | 最低覆盖率 |
|----|-----------|
| Service 层 | 80% |
| Repository 层 | 70% |
| Router 层 | 60%（集成测试覆盖核心路径） |
| shared 公共库 | 90% |

```bash
# 运行测试
pytest --cov=services --cov-report=html
```

---

## 8. Git 工作流

### 8.1 分支策略

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 生产就绪 | PR + Review + CI 通过 |
| `dev` | 开发集成 | PR + CI 通过 |
| `feature/*` | 功能开发 | 自由推送 |
| `hotfix/*` | 紧急修复 | 可直接 PR 到 main |

### 8.2 Commit 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
类型(范围): 描述

feat(content-engine): add textbook parsing endpoint
fix(auth): token refresh race condition
docs(api): update content-engine API doc
refactor(shared): extract base repository class
test(learning): add task assignment unit tests
chore(deps): upgrade fastapi to 0.111
```

**类型：**

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `docs` | 文档变更 |
| `refactor` | 重构（无功能变更） |
| `test` | 测试 |
| `chore` | 构建/依赖/配置 |
| `perf` | 性能优化 |
| `ci` | CI/CD 配置 |

### 8.3 PR 规范

- 标题遵循 Commit 规范格式
- 描述中说明：做了什么、为什么、怎么测试
- 关联 Issue（如有）：`Closes #123`
- 单个 PR 不超过 500 行改动（大功能拆分 PR）

---

## 9. 环境与依赖管理

### 9.1 依赖管理

```bash
# 使用 Poetry 管理依赖
poetry add fastapi
poetry add --group dev pytest pytest-asyncio

# 锁定版本
poetry lock
```

### 9.2 环境变量

- **不要硬编码**配置值，统一通过 Pydantic Settings 读取
- `.env` 文件不入 Git（已在 `.gitignore` 中）
- `.env.example` 提供模板

```python
# shared/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "zhiqu"
    db_user: str = "postgres"
    db_password: str = ""
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret: str = ""
    jwt_access_ttl: int = 7200       # 2h
    jwt_refresh_ttl: int = 604800    # 7d
    
    # LLM
    llm_provider: str = "deepseek"
    llm_model_chat: str = "deepseek-v3"
    llm_model_embed: str = "text-embedding-3-small"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
```

### 9.3 Python 版本

- 统一 Python 3.12+
- Docker 基础镜像：`python:3.12-slim`
- 本地开发推荐使用 `pyenv` 管理版本

---

## 10. 安全规范

### 10.1 输入校验

- **所有外部输入**必须通过 Pydantic 模型校验
- 禁止直接使用 `request.json()` 或 `request.query_params` 原始值
- SQL 查询全部使用参数化（SQLAlchemy ORM 天然满足）

### 10.2 敏感数据

| 数据 | 存储方式 | 日志处理 |
|------|----------|----------|
| 密码 | bcrypt 哈希 | 不记录 |
| 手机号 | AES-256-GCM 加密 | 脱敏：`138****1234` |
| 身份证 | AES-256-GCM 加密 | 脱敏：`3201**********1234` |
| JWT Token | 不持久化 | 脱敏：`eyJ***...` |
| API Key | 环境变量 | 不记录 |

### 10.3 认证与授权

```python
# 角色校验装饰器
def require_role(*roles: str):
    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user
    return Depends(dependency)

# 使用
@router.post("/textbooks", dependencies=[Depends(require_role("admin"))])
async def create_textbook(...):
    ...
```

### 10.4 CORS 配置

```python
# 仅允许白名单域名
CORS_ORIGINS = [
    "https://app.zhiqu.com",
    "https://admin.zhiqu.com",
    "http://localhost:3000",  # 开发环境
]
```

### 10.5 限流

```python
# Redis 滑动窗口限流
# Key 格式：rate:{user_id}:{endpoint}
# 全局：1000 QPS
# 单用户：120/min
# 短信验证码：5/min
# AI 对话：30/min
# 文件上传：10/min
```

---

## 附录 A：代码审查检查清单

- [ ] 类型标注完整
- [ ] 结构化日志（非字符串拼接）
- [ ] 敏感信息脱敏
- [ ] 异常正确处理并归类
- [ ] SQL 无 N+1 查询
- [ ] 新增/变更接口有对应测试
- [ ] Alembic 迁移可逆
- [ ] 无硬编码配置值
- [ ] Commit message 规范
- [ ] PR 不超过 500 行

---

*本文件为后端开发通用规范，各服务模块可在此基础上补充模块特定约定。*