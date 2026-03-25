# 系统架构总览

> zhiqu-classroom 架构分层、服务划分与通信模式

---

## 1. 架构风格

采用 **模块化单体 → 微服务** 渐进演化策略：

- **MVP 阶段**：所有服务部署在同一进程（FastAPI monolith），按 Python package 划分模块边界
- **成长阶段**：流量/团队规模增长后，沿模块边界拆分为独立服务
- **服务间通信**：进程内直接调用（MVP）→ HTTP/gRPC + 事件驱动（拆分后）

这样做的好处：
- 首期部署简单（单进程 + 单数据库），运维成本极低
- 模块间通过明确接口通信，拆分时改动最小
- 避免过早引入服务发现、分布式事务等复杂度

---

## 2. 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层 (Client)                         │
│  学生端 H5 (React)  │  家长端小程序 (Taro)  │  管理后台 (React)  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API 网关层 (Gateway)                         │
│  路由分发 │ JWT 认证 │ 限流 │ 请求日志 │ CORS │ 链路追踪注入      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     业务服务层 (Services)                        │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ user-profile  │  │ content-engine │  │ learning-orchestrator│  │
│  │ 用户管理       │  │ 教材+知识点    │  │ 任务编排             │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ media-gen     │  │ ai-tutor      │  │ analytics-reporting  │  │
│  │ 内容生成       │  │ AI 辅导       │  │ 统计报表             │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐                                               │
│  │ notification  │                                               │
│  │ 消息触达       │                                               │
│  └──────────────┘                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI 能力层 (AI Layer)                        │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ LLM Gateway   │  │ RAG Pipeline   │  │ Doc Parser          │  │
│  │ 模型路由/熔断  │  │ 向量检索+重排  │  │ 文档解析+OCR        │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐                            │
│  │ Prompt Mgr    │  │ Embedding Svc  │                           │
│  │ 模板管理       │  │ 向量化服务     │                           │
│  └──────────────┘  └───────────────┘                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据层 (Data Layer)                         │
│                                                                  │
│  PostgreSQL 16      Redis 7         MinIO/OSS        LLM APIs   │
│  + pgvector         缓存/队列/限流    对象存储          外部模型    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    平台支撑层 (Platform)                         │
│                                                                  │
│  配置中心 │ 健康检查 │ 监控告警 │ 审计日志 │ 异步任务 │ 安全基线   │
│  structlog │ Prometheus │ Grafana │ Loki │ OpenTelemetry          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 服务划分

### 3.1 服务清单

| 服务 | 职责 | Schema | 关键依赖 |
|------|------|--------|----------|
| **api-gateway** | 路由、认证、限流、CORS | — | Redis（限流/会话） |
| **user-profile** | 用户注册/登录、角色、学生档案、家长绑定 | `user_profile` | PostgreSQL、Redis（验证码/Token） |
| **content-engine** | 教材管理、章节解析、知识点抽取与索引 | `content` | PostgreSQL + pgvector、MinIO、LLM Gateway |
| **media-generation** | 游戏模板生成、视频脚本生成、练习题生成 | `media` | PostgreSQL、LLM Gateway、MinIO |
| **learning-orchestrator** | 任务创建/分配/进度跟踪、学习记录 | `learning` | PostgreSQL、Redis（任务状态缓存） |
| **ai-tutor** | AI 辅导对话、上下文管理、知识问答 | `ai_tutor` | PostgreSQL、LLM Gateway、RAG Pipeline |
| **analytics-reporting** | 学习统计、周报生成、班级分析 | `analytics` | PostgreSQL、Redis（聚合缓存） |
| **notification** | 短信、推送、站内信 | `notification` | Redis Streams、第三方 SMS/Push |

### 3.2 Schema 隔离策略

```sql
-- 每个服务拥有独立 PostgreSQL schema（逻辑隔离）
CREATE SCHEMA user_profile;
CREATE SCHEMA content;
CREATE SCHEMA media;
CREATE SCHEMA learning;
CREATE SCHEMA ai_tutor;
CREATE SCHEMA analytics;
CREATE SCHEMA notification;
CREATE SCHEMA platform;     -- 系统配置、审计日志、异步任务

-- MVP 阶段共享同一 PostgreSQL 实例
-- 服务只能访问自己的 schema，跨服务引用存 UUID、不建外键
```

---

## 4. 通信模式

### 4.1 同步通信（请求-响应）

MVP 阶段主要通信方式。服务间通过内部函数调用（同进程）或 HTTP REST（拆分后）。

```
客户端 ──HTTPS──► api-gateway ──内部调用──► 业务服务
                                           │
                                           ├──► LLM Gateway（模型调用）
                                           └──► RAG Pipeline（知识检索）
```

**约定：**
- 所有 API 遵循 RESTful 风格，路径 `/api/v1/{service}/{resource}`
- 请求携带 `Authorization: Bearer <JWT>` + `X-Request-ID`
- 响应统一格式：`{ "code": 0, "message": "ok", "data": {...} }`
- 超时默认 30s，LLM 相关接口 120s

### 4.2 异步通信（事件驱动）

耗时操作通过 Redis Streams 解耦：

```
生产者（业务服务）──publish──► Redis Stream ──consume──► 消费者（工作进程）
```

**核心事件流：**

| 事件 | 生产者 | 消费者 | 说明 |
|------|--------|--------|------|
| `textbook.uploaded` | content-engine | content-engine (worker) | 触发异步解析 |
| `textbook.parsed` | content-engine | media-generation | 知识点就绪，可生成内容 |
| `resource.generated` | media-generation | learning-orchestrator | 资源就绪，可创建任务 |
| `task.completed` | learning-orchestrator | analytics-reporting | 学习完成，更新统计 |
| `report.ready` | analytics-reporting | notification | 周报生成完毕，通知家长 |
| `llm.call.completed` | LLM Gateway | analytics-reporting | 记录调用日志与用量 |

**消费组模式：**

```python
# 每个消费者服务创建独立消费组，支持水平扩展
XGROUP CREATE stream:textbook.parsed media-gen-group $ MKSTREAM
XREADGROUP GROUP media-gen-group worker-1 COUNT 10 BLOCK 5000 \
    STREAMS stream:textbook.parsed >
```

**重试与死信：**
- 消费失败自动重试（指数退避，最多 5 次）
- 超过重试次数转入死信流 `stream:dead-letter`
- 详见 [异步任务设计](../platform/async-tasks.md)

### 4.3 通信模式选择矩阵

| 场景 | 模式 | 理由 |
|------|------|------|
| 用户登录/查询 | 同步 REST | 实时性要求高，延迟 <100ms |
| 教材解析 | 异步事件 | 耗时 30s-5min，不能阻塞请求 |
| LLM 内容生成 | 异步事件 | 耗时 10s-60s，需排队控制并发 |
| 学习进度更新 | 同步 REST | 用户操作触发，实时写入 |
| 统计报表生成 | 异步事件 | 定时批处理，不影响在线体验 |
| AI 对话流式 | SSE/WebSocket | 流式输出 LLM 响应 |

---

## 5. API 网关

### 5.1 职责

```
┌──────────────────────────────────────────────────────┐
│                    API Gateway                        │
│                                                       │
│  ① TLS 终结                                          │
│  ② CORS 处理                                         │
│  ③ 请求 ID 注入（X-Request-ID → X-Trace-ID）        │
│  ④ JWT 认证 + 角色提取                               │
│  ⑤ 限流（令牌桶，基于 user_id + endpoint）            │
│  ⑥ 路由分发（路径前缀 → 目标服务）                    │
│  ⑦ 请求/响应日志                                     │
│  ⑧ 全局异常处理 + 统一错误格式                       │
└──────────────────────────────────────────────────────┘
```

### 5.2 路由表

| 路径前缀 | 目标服务 | 认证 |
|----------|----------|------|
| `/api/v1/auth/*` | user-profile | ❌ 公开 |
| `/api/v1/users/*` | user-profile | ✅ JWT |
| `/api/v1/textbooks/*` | content-engine | ✅ JWT |
| `/api/v1/chapters/*` | content-engine | ✅ JWT |
| `/api/v1/knowledge-points/*` | content-engine | ✅ JWT |
| `/api/v1/games/*` | media-generation | ✅ JWT |
| `/api/v1/videos/*` | media-generation | ✅ JWT |
| `/api/v1/practices/*` | media-generation | ✅ JWT |
| `/api/v1/tasks/*` | learning-orchestrator | ✅ JWT |
| `/api/v1/learning-records/*` | learning-orchestrator | ✅ JWT |
| `/api/v1/conversations/*` | ai-tutor | ✅ JWT |
| `/api/v1/stats/*` | analytics-reporting | ✅ JWT |
| `/api/v1/reports/*` | analytics-reporting | ✅ JWT |
| `/api/v1/admin/*` | admin (多服务聚合) | ✅ JWT + admin |

### 5.3 限流策略

```yaml
rate_limits:
  global:
    requests_per_second: 1000       # 全局 QPS 上限
  per_user:
    requests_per_minute: 120        # 单用户每分钟
  per_endpoint:
    auth_sms_send:
      requests_per_minute: 5        # 短信发送限频
    llm_conversation:
      requests_per_minute: 30       # AI 对话限频
    file_upload:
      requests_per_minute: 10       # 文件上传限频
```

实现：Redis 滑动窗口算法，key 格式 `rate:{user_id}:{endpoint}`。

### 5.4 MVP 实现

首期 API 网关与业务服务合并在同一 FastAPI 应用中：

```python
# main.py — MVP 单体入口
from fastapi import FastAPI
from services.user_profile.router import router as user_router
from services.content_engine.router import router as content_router
from services.media_generation.router import router as media_router
from services.learning_orchestrator.router import router as learning_router
from services.ai_tutor.router import router as tutor_router
from services.analytics_reporting.router import router as analytics_router
from services.admin.router import router as admin_router
from shared.middleware import (
    RequestIdMiddleware,
    JWTAuthMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)

app = FastAPI(title="zhiqu-classroom", version="0.1.0")

# 中间件（执行顺序：从下往上）
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RequestIdMiddleware)

# 路由注册
app.include_router(user_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(learning_router, prefix="/api/v1")
app.include_router(tutor_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1/admin")
```

---

## 6. AI 能力层

AI 能力层是业务服务与外部 LLM 之间的抽象层，屏蔽模型差异，提供统一调用接口。

### 6.1 组件架构

```
业务服务
  │
  ├──► Prompt Manager ──► 模板渲染（Jinja2）
  │         │
  │         ▼
  ├──► LLM Gateway ──► Provider 路由 ──► DeepSeek / Qwen / OpenAI / Anthropic
  │         │                               │
  │         ├── 熔断/降级/限速              ├── 流式/批量
  │         ├── 调用日志记录                ├── Token 计量
  │         └── 成本控制                    └── 超时重试
  │
  ├──► RAG Pipeline
  │         │
  │         ├── Query 改写（LLM）
  │         ├── 向量检索（pgvector）
  │         ├── 重排序（Reranker）
  │         └── 上下文组装
  │
  ├──► Doc Parser
  │         │
  │         ├── PDF → 结构化文本（PyMuPDF + pdfplumber）
  │         ├── DOCX/PPTX → 文本（python-docx / python-pptx）
  │         └── 图片/扫描件 → OCR（PaddleOCR）
  │
  └──► Embedding Service
            │
            └── 文本 → 向量（本地模型或 API）
```

### 6.2 LLM Gateway 调用流程

```
请求进入
  │
  ├─ 1. 查路由规则 → 选择目标模型
  ├─ 2. 检查熔断状态 → 熔断则走 fallback 模型
  ├─ 3. 检查限速 → 超限则排队或拒绝
  ├─ 4. 渲染 Prompt 模板
  ├─ 5. 调用 LLM Provider API
  ├─ 6. 记录调用日志（异步写入）
  ├─ 7. Token 计量 + 费用计算
  └─ 8. 返回结果（或流式推送）
```

详见 [LLM 模型管理](../platform/llm-management.md)、[LLM 用量统计](../platform/llm-usage.md)。

---

## 7. 安全架构

### 7.1 认证流程

```
              短信验证码登录
┌────────┐    ┌─────────────┐    ┌──────────────┐
│ 客户端  │───►│  发送验证码   │───►│  Redis 存储   │
│         │    │  POST /sms   │    │  5分钟过期    │
│         │    └─────────────┘    └──────────────┘
│         │
│         │    ┌─────────────┐    ┌──────────────┐    ┌──────────┐
│         │───►│  验证+登录    │───►│  校验验证码   │───►│ 签发 JWT  │
│         │    │  POST /verify│    │  Redis 查询   │    │ access +  │
│         │    └─────────────┘    └──────────────┘    │ refresh   │
│         │                                           └──────────┘
│         │
│         │              微信登录
│         │    ┌─────────────┐    ┌──────────────┐    ┌──────────┐
│         │───►│  微信授权回调 │───►│  换取 openid  │───►│ 查找/创建 │
│         │    │  GET /wx/cb  │    │  微信 API     │    │ 用户+JWT │
└────────┘    └─────────────┘    └──────────────┘    └──────────┘
```

### 7.2 JWT Token 结构

```json
{
  "sub": "user_uuid_v7",
  "role": "student",            // student | guardian | admin
  "device_id": "device_hash",
  "iat": 1711353600,
  "exp": 1711360800             // access: 2h, refresh: 7d
}
```

### 7.3 安全边界

| 层级 | 措施 |
|------|------|
| **传输层** | 全链路 HTTPS（TLS 1.3）、HSTS |
| **认证层** | JWT + 刷新令牌轮换、设备指纹绑定 |
| **授权层** | 基于角色的访问控制（RBAC），数据行级隔离 |
| **数据层** | 敏感字段加密存储（AES-256-GCM）、SQL 参数化 |
| **应用层** | 输入校验（Pydantic）、限流、CORS 白名单 |
| **运维层** | 密钥通过环境变量注入、审计日志、依赖漏洞扫描 |

详见 [安全基线](../platform/security.md)。

---

## 8. 演进路线

### 8.1 MVP → V1 → V2

| 阶段 | 时间 | 架构 | 部署 | 重点 |
|------|------|------|------|------|
| **MVP** | 0-3月 | 模块化单体 | 单机 Docker Compose | 核心功能闭环 |
| **V1** | 3-6月 | 单体 + 独立 Worker | 2-3 台云服务器 | AI 功能完善、性能优化 |
| **V2** | 6-12月 | 服务拆分 | K8s 集群 | 水平扩展、高可用 |

### 8.2 拆分触发条件

当出现以下任一情况时，考虑将模块拆分为独立服务：

1. **性能瓶颈**：某模块 CPU/内存占用影响其他模块
2. **团队扩张**：3+ 开发者同时修改同一模块
3. **独立伸缩**：如 media-generation 需要 GPU 实例
4. **故障隔离**：如 LLM 调用超时不应拖垮用户登录

### 8.3 拆分路径

```
Phase 0 (MVP)                    Phase 1                      Phase 2
┌─────────────────┐        ┌─────────────────┐         ┌──────────────┐
│   monolith      │        │   monolith      │         │ user-profile │
│                 │        │  (core APIs)    │         │ content-eng  │
│ all services    │  ──►   │                 │   ──►   │ learning-orc │
│ in one process  │        │ + worker        │         │ media-gen    │
│                 │        │  (async tasks)  │         │ ai-tutor     │
│                 │        │  (独立进程)      │         │ analytics    │
└─────────────────┘        └─────────────────┘         └──────────────┘
```

**Phase 1 优先拆出 Worker 的原因：**
- media-generation 和 content-engine 的异步任务（教材解析、内容生成）是最耗资源的
- 拆成独立 Worker 进程，不影响在线 API 响应
- 只需增加一个进程，无需引入服务发现