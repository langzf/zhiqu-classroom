# 模型配置模块设计文档

> 版本: v0.1 | 日期: 2026-04-06 | 状态: 设计阶段

## 1. 背景与目标

### 1.1 背景

智趣课堂系统中多个业务模块依赖大语言模型（LLM）能力：

| 模块 | 当前状态 | 模型用途 |
|------|----------|----------|
| **教材解析** (`content_service.parse_textbook`) | 已实现，硬编码 `gpt-4o-mini` | 解析教材章节结构、提取知识点 |
| **知识点提取** (`content_service.extract_knowledge_points`) | 已实现，硬编码 `gpt-4o-mini` | 从章节内容中提取结构化知识点 |
| **媒体/游戏生成** (`media-generation`) | 规划中 | 基于知识点生成游戏脚本、视频脚本、练习题 |
| **学习辅助** (`learning_service`) | 规划中 | 自适应学习路径、智能推荐 |

当前问题：
- 模型名称硬编码在 `llm_client.py` 和各 service 中，无法动态切换
- 不同场景对模型能力需求不同（解析需要强推理，生成需要创造力），但无法分别配置
- 管理员无法在后台调整模型配置，每次修改需重新部署
- 缺少对多供应商（OpenAI、Anthropic、本地模型等）的统一抽象

### 1.2 目标

1. **管理后台可配置** — 管理员可通过后台 UI 增删改查模型配置，无需修改代码
2. **按场景绑定** — 每个业务场景（教材解析、知识点提取、游戏生成等）可独立指定使用的模型
3. **多供应商支持** — 统一抽象层支持 OpenAI、Anthropic、国产大模型（通义千问、文心一言等）及兼容 OpenAI 接口的第三方
4. **运行时生效** — 修改配置后无需重启服务即可生效
5. **安全** — API Key 等敏感信息加密存储，前端不暴露

## 2. 核心概念

### 2.1 领域模型

```
┌─────────────────────────────────────────────────┐
│                 ModelProvider                     │
│  (供应商: OpenAI / Anthropic / Custom)           │
│                                                   │
│  - id, name, provider_type                       │
│  - base_url, api_key (加密)                      │
│  - is_active, created_at, updated_at             │
└──────────────────────┬──────────────────────────┘
                       │ 1:N
                       ▼
┌─────────────────────────────────────────────────┐
│                 ModelConfig                       │
│  (具体模型: gpt-4o, claude-3.5-sonnet, etc.)    │
│                                                   │
│  - id, provider_id (FK)                          │
│  - model_name, display_name                      │
│  - capabilities: [chat, vision, embedding, tts]  │
│  - default_params: {temperature, max_tokens...}  │
│  - is_active, sort_order                         │
│  - created_at, updated_at                        │
└──────────────────────┬──────────────────────────┘
                       │ 1:N
                       ▼
┌─────────────────────────────────────────────────┐
│              SceneModelBinding                    │
│  (场景绑定: 哪个场景用哪个模型)                  │
│                                                   │
│  - id, scene_key (唯一)                          │
│  - model_config_id (FK)                          │
│  - param_overrides: {temperature, ...}           │
│  - is_active                                     │
│  - created_at, updated_at                        │
└─────────────────────────────────────────────────┘
```

### 2.2 预定义场景 (Scene)

场景是系统内对"模型用途"的枚举标识，新增业务模块时只需注册新的 `scene_key`：

| scene_key | 说明 | 推荐能力 |
|-----------|------|----------|
| `content.parse_textbook` | 教材结构解析 | chat, 强推理 |
| `content.extract_knowledge` | 知识点提取 | chat, 结构化输出 |
| `media.generate_game` | 游戏脚本生成 | chat, 创造力 |
| `media.generate_video_script` | 视频脚本生成 | chat, 创造力 |
| `media.generate_exercise` | 练习题生成 | chat, 结构化输出 |
| `learning.adaptive_path` | 自适应学习路径 | chat, 推理 |
| `learning.qa_assistant` | 答疑助手 | chat, 多轮对话 |

### 2.3 供应商类型 (ProviderType)

```python
class ProviderType(str, Enum):
    OPENAI = "openai"               # OpenAI 官方
    OPENAI_COMPATIBLE = "openai_compatible"  # 兼容 OpenAI 接口的第三方 (如 DeepSeek, 零一万物)
    ANTHROPIC = "anthropic"         # Anthropic Claude
    QWEN = "qwen"                   # 通义千问
    LOCAL = "local"                 # 本地部署 (Ollama, vLLM 等)
```

## 3. 数据库设计

### 3.1 `model_providers` 表

```sql
CREATE TABLE model_providers (
    id          TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name        TEXT NOT NULL,                    -- 显示名称, 如 "OpenAI 官方"
    provider_type TEXT NOT NULL,                  -- 枚举: openai, anthropic, qwen, openai_compatible, local
    base_url    TEXT,                             -- API 基础地址, OpenAI 可为空(使用默认)
    api_key_enc TEXT,                             -- 加密后的 API Key
    is_active   INTEGER NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 3.2 `model_configs` 表

```sql
CREATE TABLE model_configs (
    id           TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    provider_id  TEXT NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
    model_name   TEXT NOT NULL,                   -- 实际模型名, 如 "gpt-4o", "claude-3-5-sonnet-20241022"
    display_name TEXT NOT NULL,                   -- 前端显示名, 如 "GPT-4o"
    capabilities TEXT NOT NULL DEFAULT '["chat"]', -- JSON 数组: chat, vision, embedding, tts, stt
    default_params TEXT NOT NULL DEFAULT '{}',     -- JSON: {"temperature": 0.7, "max_tokens": 4096}
    is_active    INTEGER NOT NULL DEFAULT 1,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(provider_id, model_name)
);
```

### 3.3 `scene_model_bindings` 表

```sql
CREATE TABLE scene_model_bindings (
    id              TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    scene_key       TEXT NOT NULL UNIQUE,          -- 场景标识, 如 "content.parse_textbook"
    model_config_id TEXT NOT NULL REFERENCES model_configs(id) ON DELETE RESTRICT,
    param_overrides TEXT NOT NULL DEFAULT '{}',     -- JSON: 覆盖默认参数
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## 4. API 设计

### 4.1 供应商管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/model-providers` | 列表（分页） |
| `POST` | `/admin/model-providers` | 新建供应商 |
| `GET` | `/admin/model-providers/{id}` | 详情 |
| `PUT` | `/admin/model-providers/{id}` | 更新 |
| `DELETE` | `/admin/model-providers/{id}` | 删除（仅无关联模型时） |
| `POST` | `/admin/model-providers/{id}/test` | 测试连接 |

### 4.2 模型配置

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/model-configs` | 列表（支持按 provider_id 筛选） |
| `POST` | `/admin/model-configs` | 新建模型 |
| `GET` | `/admin/model-configs/{id}` | 详情 |
| `PUT` | `/admin/model-configs/{id}` | 更新 |
| `DELETE` | `/admin/model-configs/{id}` | 删除（仅无绑定时） |

### 4.3 场景绑定

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/scene-bindings` | 列表（含场景描述） |
| `PUT` | `/admin/scene-bindings/{scene_key}` | 设置/更新场景绑定 |
| `DELETE` | `/admin/scene-bindings/{scene_key}` | 解除绑定（回退到默认） |
| `GET` | `/admin/scenes` | 列出所有预定义场景（含绑定状态） |

### 4.4 请求/响应示例

#### 创建供应商

```json
// POST /admin/model-providers
{
    "name": "OpenAI 官方",
    "provider_type": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-xxx..."
}

// Response
{
    "code": 0,
    "data": {
        "id": "a1b2c3...",
        "name": "OpenAI 官方",
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_masked": "sk-***...xxx",
        "is_active": true,
        "created_at": "2026-04-06T18:00:00Z"
    }
}
```

#### 创建模型配置

```json
// POST /admin/model-configs
{
    "provider_id": "a1b2c3...",
    "model_name": "gpt-4o",
    "display_name": "GPT-4o",
    "capabilities": ["chat", "vision"],
    "default_params": {
        "temperature": 0.7,
        "max_tokens": 4096
    }
}
```

#### 设置场景绑定

```json
// PUT /admin/scene-bindings/content.parse_textbook
{
    "model_config_id": "m1n2o3...",
    "param_overrides": {
        "temperature": 0.3,
        "max_tokens": 8192
    }
}
```

## 5. 服务层设计

### 5.1 模型解析流程

业务代码调用模型时，不再硬编码模型名，而是通过场景 key 自动解析：

```
业务代码                     ModelConfigService              LLMClient
   │                              │                            │
   │  get_model("content.parse")  │                            │
   │─────────────────────────────>│                            │
   │                              │  查询 scene_model_bindings │
   │                              │  + model_configs           │
   │                              │  + model_providers         │
   │                              │                            │
   │  ResolvedModel               │                            │
   │<─────────────────────────────│                            │
   │                              │                            │
   │  chat(resolved_model, msgs)  │                            │
   │──────────────────────────────────────────────────────────>│
   │                              │                  根据 provider_type│
   │                              │                  选择对应 client   │
   │  response                    │                            │
   │<──────────────────────────────────────────────────────────│
```

### 5.2 核心类设计

```python
# services/application/services/model_config_service.py

@dataclass
class ResolvedModel:
    """解析后的完整模型信息，业务代码直接使用"""
    provider_type: str          # "openai", "anthropic", ...
    base_url: str | None
    api_key: str                # 解密后的明文 key
    model_name: str             # "gpt-4o"
    params: dict                # 合并后的参数 (default_params + param_overrides)


class ModelConfigService:
    """模型配置服务 — 负责解析场景到具体模型"""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db
        self._cache: dict[str, tuple[ResolvedModel, float]] = {}  # scene_key -> (model, expire_ts)
        self._cache_ttl = 300  # 5 分钟缓存

    async def resolve(self, scene_key: str) -> ResolvedModel:
        """根据场景 key 解析出完整模型信息（带缓存）"""
        ...

    async def invalidate_cache(self, scene_key: str | None = None):
        """配置变更时清除缓存"""
        ...

    # CRUD 方法
    async def list_providers(self, ...) -> PagedResult: ...
    async def create_provider(self, data: CreateProviderRequest) -> Provider: ...
    async def update_provider(self, id: str, data: UpdateProviderRequest) -> Provider: ...
    async def delete_provider(self, id: str) -> None: ...
    async def test_provider(self, id: str) -> TestResult: ...

    async def list_models(self, provider_id: str | None = None) -> list[ModelConfig]: ...
    async def create_model(self, data: CreateModelRequest) -> ModelConfig: ...
    async def update_model(self, id: str, data: UpdateModelRequest) -> ModelConfig: ...
    async def delete_model(self, id: str) -> None: ...

    async def list_bindings(self) -> list[SceneBinding]: ...
    async def set_binding(self, scene_key: str, data: SetBindingRequest) -> SceneBinding: ...
    async def remove_binding(self, scene_key: str) -> None: ...
```

### 5.3 改造后的 LLMClient

```python
# services/shared/llm_client.py (改造后)

class LLMClient:
    """统一的 LLM 调用客户端，支持多供应商"""

    async def chat(
        self,
        resolved: ResolvedModel,
        messages: list[dict],
        **kwargs
    ) -> str:
        """根据 resolved model 信息路由到对应供应商 SDK"""
        merged_params = {**resolved.params, **kwargs}

        match resolved.provider_type:
            case "openai" | "openai_compatible":
                return await self._call_openai(resolved, messages, merged_params)
            case "anthropic":
                return await self._call_anthropic(resolved, messages, merged_params)
            case _:
                raise ValueError(f"Unsupported provider: {resolved.provider_type}")

    async def _call_openai(self, resolved, messages, params) -> str:
        client = AsyncOpenAI(
            api_key=resolved.api_key,
            base_url=resolved.base_url
        )
        resp = await client.chat.completions.create(
            model=resolved.model_name,
            messages=messages,
            **params
        )
        return resp.choices[0].message.content

    async def _call_anthropic(self, resolved, messages, params) -> str:
        # Anthropic SDK 调用（消息格式需转换）
        ...
```

### 5.4 业务代码改造示例

**改造前** (content_service.py)：

```python
# 硬编码模型名
async def parse_textbook(self, textbook_id: str):
    response = await self.llm_client.chat(
        model="gpt-4o-mini",
        messages=[...],
        temperature=0.3,
    )
```

**改造后**：

```python
async def parse_textbook(self, textbook_id: str):
    resolved = await self.model_config_service.resolve("content.parse_textbook")
    response = await self.llm_client.chat(
        resolved=resolved,
        messages=[...],
        # temperature 等参数已在 resolved.params 中，也可覆盖
    )
```

## 6. API Key 安全方案

### 6.1 加密存储

- 使用 `Fernet` 对称加密（`cryptography` 库），密钥来自环境变量 `ENCRYPTION_KEY`
- 数据库仅存储 `api_key_enc`（密文），明文仅在内存中存在
- API 返回时只显示 `api_key_masked`（如 `sk-***...xxx`），不返回明文或密文

```python
# services/shared/crypto.py

from cryptography.fernet import Fernet
import os

_fernet = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get("ENCRYPTION_KEY")
        if not key:
            # MVP 阶段: 自动生成并写入 .env
            key = Fernet.generate_key().decode()
            # 提示管理员保存此 key
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet

def encrypt_api_key(plain: str) -> str:
    return get_fernet().encrypt(plain.encode()).decode()

def decrypt_api_key(cipher: str) -> str:
    return get_fernet().decrypt(cipher.encode()).decode()

def mask_api_key(plain: str) -> str:
    if len(plain) <= 8:
        return "***"
    return f"{plain[:3]}***{plain[-4:]}"
```

### 6.2 安全约束

1. **API 层**: `api_key` 仅在创建/更新时接收明文，响应永远只返回 `api_key_masked`
2. **Service 层**: `resolve()` 返回的 `ResolvedModel` 含明文 key，仅在服务进程内存中
3. **日志**: 禁止记录 API Key 明文，structlog processor 自动脱敏

## 7. 缓存与一致性

### 7.1 缓存策略

- `ModelConfigService` 维护内存缓存，TTL 5 分钟
- 管理员通过 API 修改配置后，主动 `invalidate_cache()`
- 单实例部署（当前架构），无需分布式缓存

### 7.2 回退策略

当场景未绑定模型时，按以下顺序回退：

1. 查 `scene_model_bindings` → 有绑定则使用
2. 查全局默认（`scene_key = "__default__"`）→ 有则使用
3. 查环境变量 `OPENAI_API_KEY` + `OPENAI_BASE_URL` → 有则用 `gpt-4o-mini`（兼容当前行为）
4. 抛出 `ModelNotConfiguredError`

## 8. 文件结构

```
services/
├── domain/
│   └── schemas/
│       └── model_config.py          # Pydantic schemas (请求/响应)
├── infrastructure/
│   └── persistence/
│       └── models/
│           └── model_config.py      # SQLAlchemy / aiosqlite 模型
├── application/
│   └── services/
│       └── model_config_service.py  # 核心业务逻辑
├── interfaces/
│   └── api/
│       └── admin/
│           └── model_config.py      # FastAPI 路由
├── shared/
│   ├── llm_client.py               # 改造: 支持 ResolvedModel
│   └── crypto.py                    # 新增: 加密工具
└── docs/
    └── design/
        └── model-config-module.md   # 本文档
```

## 9. 数据迁移

### 9.1 建表 SQL

```sql
-- migrations/003_model_config.sql

CREATE TABLE IF NOT EXISTS model_providers (
    id          TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name        TEXT NOT NULL,
    provider_type TEXT NOT NULL CHECK(provider_type IN ('openai','openai_compatible','anthropic','qwen','local')),
    base_url    TEXT,
    api_key_enc TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS model_configs (
    id           TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    provider_id  TEXT NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
    model_name   TEXT NOT NULL,
    display_name TEXT NOT NULL,
    capabilities TEXT NOT NULL DEFAULT '["chat"]',
    default_params TEXT NOT NULL DEFAULT '{}',
    is_active    INTEGER NOT NULL DEFAULT 1,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(provider_id, model_name)
);

CREATE TABLE IF NOT EXISTS scene_model_bindings (
    id              TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    scene_key       TEXT NOT NULL UNIQUE,
    model_config_id TEXT NOT NULL REFERENCES model_configs(id) ON DELETE RESTRICT,
    param_overrides TEXT NOT NULL DEFAULT '{}',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_model_configs_provider ON model_configs(provider_id);
CREATE INDEX IF NOT EXISTS idx_scene_bindings_model ON scene_model_bindings(model_config_id);
```

### 9.2 种子数据

首次部署时自动插入当前环境变量中的 OpenAI 配置作为默认供应商和模型：

```python
async def seed_default_model(db):
    """从环境变量迁移当前硬编码的模型配置"""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    if not api_key:
        return  # 无现有配置，跳过

    # 创建默认 Provider
    provider_id = await create_provider(db, name="OpenAI", type="openai", base_url=base_url, api_key=api_key)

    # 创建默认 Model
    model_id = await create_model(db, provider_id=provider_id, model_name="gpt-4o-mini", display_name="GPT-4o Mini")

    # 绑定现有场景
    for scene in ["content.parse_textbook", "content.extract_knowledge"]:
        await set_binding(db, scene_key=scene, model_config_id=model_id)
```

## 10. 实施计划

### Phase 1: 基础设施（1-2 天）
- [ ] 创建数据库表 + 迁移脚本
- [ ] 实现 `crypto.py`（加密/解密/脱敏）
- [ ] 实现 `ModelConfigService`（CRUD + `resolve()`）
- [ ] 实现 admin API 路由

### Phase 2: LLM Client 改造（1 天）
- [ ] 改造 `llm_client.py` 支持 `ResolvedModel`
- [ ] 改造 `content_service.py` 使用 `resolve()` 替代硬编码
- [ ] 保持向后兼容（环境变量回退）

### Phase 3: 管理后台 UI（1-2 天）
- [ ] 供应商管理页面（列表 + 新增/编辑 Modal）
- [ ] 模型配置页面（按供应商分组）
- [ ] 场景绑定页面（下拉选择模型 + 参数覆盖）
- [ ] 连接测试功能

### Phase 4: 验证与完善（0.5 天）
- [ ] 端到端测试：管理后台配置模型 → 教材解析使用新模型
- [ ] API Key 脱敏验证
- [ ] 缓存失效验证

## 11. 开放问题

1. **是否需要模型用量统计？** — 记录每次调用的 token 数、耗时、花费，用于成本监控
2. **是否需要模型灰度切换？** — 如按比例将 10% 请求路由到新模型做 A/B 测试
3. **Embedding 模型是否纳入？** — 当前系统暂无 embedding 需求，后续知识检索可能需要
4. **是否支持多模型串联？** — 如先用便宜模型粗筛，再用贵模型精炼（chain of models）

---

> 下一步: 确认设计方案后，开始 Phase 1 实施。