# 技术选型文档（v1.0）

> 适用范围：zhiqu-classroom MVP 阶段

---

## 1. 选型原则

| 原则 | 说明 |
|------|------|
| **MVP 优先** | 选型服务首期需求，避免过度设计；保留向上扩展路径 |
| **团队匹配** | 优先选用 Python/TypeScript 生态，覆盖 AI + Web 双栈 |
| **云中立** | 不绑定特定云厂商 API，优先开源或可自部署组件 |
| **成本可控** | 初期使用单机/少量实例部署，按流量弹性扩展 |

---

## 2. 后端

### 2.1 编程语言与框架

| 层面 | 选型 | 理由 |
|------|------|------|
| **业务服务** | **Python 3.12 + FastAPI** | AI 生态天然支持；async 性能足够；类型提示 + Pydantic 校验开箱即用 |
| **API Gateway** | **Python FastAPI** (首期合并) / Kong / APISIX (后期独立) | 首期业务量小，网关逻辑合并到一个 FastAPI 入口即可；流量增长后拆出独立网关 |
| **共享库 (shared)** | Python package（monorepo 内部引用） | DTO、错误码、事件 schema、工具函数统一维护 |

### 2.2 数据库

| 用途 | 选型 | 理由 |
|------|------|------|
| **关系数据** | **PostgreSQL 16** | 功能全面，JSONB 灵活，向量扩展 pgvector 可选，社区活跃 |
| **向量检索** | **pgvector 扩展**（首期）/ Milvus（后期） | 首期数据量 <100 万知识点片段，pgvector 足够；后期规模化切 Milvus |
| **缓存** | **Redis 7** | 会话、Token、限流、任务状态缓存 |
| **对象存储** | **MinIO**（自部署）/ 阿里云 OSS / AWS S3 | 存教材原文件、生成素材；API 兼容 S3 协议，可平滑迁移 |

### 2.3 消息队列 / 事件总线

| 选型 | 理由 |
|------|------|
| **Redis Streams**（首期） | 已引入 Redis，首期事件量不大，Streams 即可满足发布/消费、消费组、ACK |
| **RabbitMQ / Kafka**（后期） | 事件量级超过 Redis Streams 合理范围后升级 |

### 2.4 ORM 与数据迁移

| 选型 | 理由 |
|------|------|
| **SQLAlchemy 2.0** (async) | Python 生态主流 ORM，支持 asyncio |
| **Alembic** | 数据库 schema 版本管理 |

---

## 3. AI 能力层

### 3.1 LLM 选型

| 场景 | 选型 | 理由 |
|------|------|------|
| **知识点抽取 / 内容生成** | **DeepSeek-V3** (主力) + **Qwen-2.5** (备选) | 中文教育场景理解能力强，API 成本可控 |
| **质量评估 / 复杂推理** | **Claude 3.5 Sonnet** / **GPT-4o** (按需调用) | 用于关键环节的二次校验，成本敏感场景不常规使用 |
| **接入方式** | 统一封装 `LLMClient`，支持多 provider 切换 | OpenAI-compatible API 统一调用，provider 降级/切换透明 |

### 3.2 文档解析

| 能力 | 选型 | 理由 |
|------|------|------|
| **PDF 解析** | **PyMuPDF (fitz)** + **pdfplumber** | 结构化文本 + 表格提取 |
| **Word/PPT 解析** | **python-docx** / **python-pptx** | 轻量级，社区成熟 |
| **OCR** | **PaddleOCR** | 中文 OCR 精度高，可本地部署，无 API 依赖 |
| **文档智能** | LLM 辅助结构化（章节/标题/层级识别） | 解析结果 + LLM 二次整理 |

### 3.3 RAG Pipeline

| 组件 | 选型 | 理由 |
|------|------|------|
| **文本切片** | **LangChain TextSplitter** (RecursiveCharacter) | 支持按标题/段落/字符多策略切片 |
| **Embedding** | **bge-large-zh-v1.5** (本地部署) | 中文语义检索 SOTA 级，1024 维，可离线运行 |
| **向量库** | pgvector（首期） | 见 2.2 |
| **检索策略** | 混合检索：向量相似度 + 关键词 BM25 | 提升召回率，减少纯语义检索漏查 |
| **重排序** | **bge-reranker-large**（可选） | 对 top-k 结果精排，提升生成质量 |

### 3.4 Prompt 管理

| 选型 | 理由 |
|------|------|
| **Jinja2 模板** + 数据库版本管理 | 模板与代码解耦，支持 A/B 测试、回滚 |
| 按 `(学科, 学段, 任务类型)` 维度组织 | 便于分场景优化 |

---

## 4. 前端

### 4.1 学生端

| 维度 | 选型 | 理由 |
|------|------|------|
| **平台** | **移动端 H5**（首期）→ 原生 App（后期） | MVP 快速验证，跨平台 |
| **框架** | **React 18 + TypeScript** | 生态丰富，组件复用性强 |
| **移动适配** | **Capacitor**（后期包装原生壳） | H5 → 原生壳平滑过渡 |
| **UI 库** | **Ant Design Mobile** | 移动端组件齐全，中文文档 |
| **游戏渲染** | **Phaser 3**（轻量 2D 游戏引擎） | 选择闯关/拖拽配对等互动用 Canvas 渲染 |
| **状态管理** | **Zustand** | 轻量，TS 友好 |
| **HTTP 客户端** | **Axios** + **React Query (TanStack Query)** | 请求缓存、自动重试、loading 状态管理 |

### 4.2 家长端

| 维度 | 选型 | 理由 |
|------|------|------|
| **平台** | **微信小程序**（首期） | 家长群体使用门槛最低 |
| **框架** | **Taro 3 (React)** | 可复用学生端部分组件，跨端能力 |

### 4.3 管理后台

| 维度 | 选型 | 理由 |
|------|------|------|
| **框架** | **React 18 + Ant Design Pro** | 表单/表格/图表开箱即用 |
| **图表** | **ECharts** | 数据看板、学习效果图表 |

---

## 5. 认证与安全

| 维度 | 选型 | 理由 |
|------|------|------|
| **认证协议** | **JWT (access + refresh token)** | 无状态，易于微服务间传递 |
| **密码存储** | **bcrypt** | 业界标准 |
| **登录方式** | 手机号 + 短信验证码（首期）；微信 OAuth（家长小程序） | 学生群体无邮箱，手机号最实际 |
| **权限模型** | **RBAC**（角色: admin / teacher / student / parent） | 首期 4 角色足够 |
| **请求签名** | 服务间调用携带内部 service-token | 内网零信任基础 |

---

## 6. 基础设施与部署

### 6.1 容器化

| 选型 | 理由 |
|------|------|
| **Docker** + **Docker Compose**（首期） | 本地开发与单机部署统一 |
| **Kubernetes**（后期） | 流量增长后切入 |

### 6.2 CI/CD

| 选型 | 理由 |
|------|------|
| **GitHub Actions** | 代码托管在 GitHub，原生集成 |
| 流水线：lint → test → build image → push → deploy | 标准流程 |

### 6.3 可观测性

| 维度 | 选型 | 理由 |
|------|------|------|
| **日志** | **structlog** (Python) → JSON → **Loki** | 结构化日志，集中查询 |
| **指标** | **Prometheus** + **Grafana** | 开源标配 |
| **链路追踪** | **OpenTelemetry** → **Jaeger** | 服务间调用可视化 |

### 6.4 开发工具

| 工具 | 用途 |
|------|------|
| **Ruff** | Python lint + format |
| **mypy** | 类型检查 |
| **pytest** + **pytest-asyncio** | 单测 |
| **ESLint** + **Prettier** | 前端 lint + format |
| **pre-commit hooks** | 提交前自动校验 |

---

## 7. Monorepo 结构（更新）

```
zhiqu-classroom/
├── app/                      # 学生端 H5 (React)
├── mini-app/                 # 家长端小程序 (Taro)
├── admin/                    # 管理后台 (Ant Design Pro)
├── services/
│   ├── shared/               # 公共库 (Python package)
│   │   ├── models/           # Pydantic DTO
│   │   ├── errors/           # 错误码
│   │   ├── events/           # 事件 schema
│   │   └── utils/            # 工具函数
│   ├── api-gateway/          # FastAPI 网关
│   ├── content-engine/       # 教材解析 + 知识点
│   ├── media-generation/     # 内容生成
│   ├── learning-orchestrator/# 任务编排
│   ├── user-profile/         # 用户管理
│   ├── analytics-reporting/  # 统计报表
│   └── notification/         # 消息触达
├── infra/                    # Docker Compose、K8s manifests
├── docs/                     # 设计文档
├── scripts/                  # 工具脚本
└── pyproject.toml            # Python monorepo 根配置
```

---

## 8. 版本与兼容性

| 组件 | 最低版本 | 备注 |
|------|----------|------|
| Python | 3.12 | 类型提示、性能改进 |
| Node.js | 20 LTS | 前端构建 |
| PostgreSQL | 16 | pgvector 0.7+ |
| Redis | 7.0 | Streams 改进 |
| Docker | 24+ | Compose V2 |
