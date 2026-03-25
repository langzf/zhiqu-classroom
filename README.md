# 知趣课堂 (zhiqu-classroom)

> AI 驱动的 K12 课后辅导平台 — 让每个孩子都有自己的 AI 老师

---

## 🎯 项目简介

知趣课堂是一个面向 K12 学生的智能课后辅导平台。教师上传教材后，系统自动解析知识点，通过 AI 生成游戏化互动内容和个性化练习，并提供 AI 辅导对话，帮助学生在课后高效巩固学习。

### 核心能力

- **📚 教材智能解析** — 上传教材 → 自动提取章节结构与知识点 → 向量化存储
- **🎮 互动内容生成** — AI 生成游戏化练习、视频脚本、个性化题目
- **🤖 AI 辅导对话** — 基于知识点的智能问答，支持多轮苏格拉底式引导
- **📊 学习数据分析** — 学习记录追踪、薄弱知识点识别、周报生成
- **👨‍👩‍👧 家长端同步** — 实时掌握孩子学习进度和报告

### 用户角色

| 角色 | 入口 | 说明 |
|------|------|------|
| 学生 | H5 页面 (React) | 完成任务、互动学习、AI 对话 |
| 家长 | 微信小程序 (Taro) | 查看学习报告、管理绑定 |
| 教师/管理员 | 管理后台 (React) | 上传教材、管理内容、查看统计 |

---

## 🏗️ 技术架构

采用 **模块化单体 → 微服务** 渐进演化策略，MVP 阶段以单进程部署降低运维成本。

```
客户端 (H5 / 小程序 / 管理后台)
         │ HTTPS
         ▼
┌─────────────────────────────┐
│      API Gateway (:8000)    │  路由 · JWT 认证 · 限流 · CORS
└──────────┬──────────────────┘
           │
     ┌─────┼─────┬──────┬──────┬──────┬───────┐
     ▼     ▼     ▼      ▼      ▼      ▼       ▼
   user  content media  ai   learning analytics notification
  profile engine  gen  tutor  orch    reporting
  :8001  :8002  :8003  :8004  :8005   :8006    :8007
           │
     ┌─────┼──────┬──────────┐
     ▼     ▼      ▼          ▼
   PostgreSQL  Redis  MinIO  LLM API
   (pgvector)              (OpenAI等)
```

### 技术栈

| 层面 | 选型 |
|------|------|
| **后端框架** | Python 3.12 + FastAPI |
| **数据库** | PostgreSQL 16 + pgvector |
| **缓存/队列** | Redis 7 (缓存 + Streams 事件总线) |
| **对象存储** | MinIO (S3 兼容) |
| **AI/LLM** | OpenAI GPT-4o / text-embedding-3-small |
| **学生端** | React H5 |
| **家长端** | Taro 微信小程序 |
| **管理后台** | React |
| **部署** | Docker Compose (MVP) → K8s (规模期) |

---

## 📁 项目结构

```
zhiqu-classroom/
├── docs/                     # 项目文档
│   ├── architecture/         #   架构设计 (系统总览、服务详情、数据流、部署)
│   ├── api/                  #   API 接口文档 (113 个接口)
│   ├── data-model/           #   数据模型 DDL (7 个域)
│   ├── tech-stack.md         #   技术选型
│   ├── logging-design.md     #   日志设计
│   └── STRUCTURE.md          #   文档结构索引
│
├── services/                 # 后端服务
│   ├── api-gateway/          #   API 网关
│   ├── content-engine/       #   内容引擎（教材解析 + 知识点）
│   ├── media-generation/     #   媒体生成（互动内容）
│   ├── learning-orchestrator/#   学习编排（任务管理）
│   ├── user-profile/         #   用户服务
│   ├── analytics-reporting/  #   数据分析
│   ├── notification/         #   通知服务
│   └── shared/               #   共享库（DTO、错误码、工具）
│
├── app/                      # 学生端 H5
├── admin/                    # 管理后台
└── scripts/                  # 工具脚本
```

> 详细文档结构参见 [docs/STRUCTURE.md](docs/STRUCTURE.md)

---

## 🚀 快速开始

### 环境要求

- Docker 24+ & Docker Compose v2
- Python 3.12+（本地开发时）
- Node.js 20+（前端开发时）

### 本地启动

```bash
# 1. 克隆项目
git clone https://github.com/your-org/zhiqu-classroom.git
cd zhiqu-classroom

# 2. 复制环境变量
cp .env.example .env
# 编辑 .env 填入必要配置（LLM API Key 等）

# 3. 启动基础设施
docker compose up -d postgres redis minio

# 4. 初始化数据库
docker compose run --rm api-gateway python -m scripts.init_db

# 5. 启动所有服务
docker compose up -d

# 6. 验证
curl http://localhost:8000/health
# 应返回: {"status": "healthy", ...}
```

### 关键环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `APP_ENV` | 运行环境 | `development` |
| `DB_USER` / `DB_PASSWORD` | 数据库凭据 | `zhiqu` / `***` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | 对象存储凭据 | — |
| `LLM_PROVIDER` | LLM 服务商 | `openai` |
| `LLM_MODEL_CHAT` | 对话模型 | `gpt-4o` |
| `LLM_MODEL_EMBED` | 向量模型 | `text-embedding-3-small` |
| `JWT_SECRET` | JWT 签名密钥 | — |
| `SMS_PROVIDER` | 短信服务商 | `aliyun` |

> 完整变量清单见 [deployment.md 环境变量章节](docs/architecture/deployment.md)

---

## 📖 文档导航

| 文档 | 说明 |
|------|------|
| [系统架构总览](docs/architecture/system-overview.md) | 分层设计、服务拓扑、通信机制 |
| [服务详细设计](docs/architecture/service-detail.md) | 8 个服务的职责、接口、依赖 |
| [核心数据流](docs/architecture/data-flow.md) | 教材解析、内容生成等 5 条核心流程 |
| [部署方案](docs/architecture/deployment.md) | Docker Compose、CI/CD、监控、运维 |
| [API 接口文档](docs/api/README.md) | 113 个接口的完整定义 |
| [数据模型](docs/data-model/README.md) | 7 个域的 DDL、索引、约束 |
| [技术选型](docs/tech-stack.md) | 技术栈决策及理由 |
| [日志设计](docs/logging-design.md) | 日志格式、脱敏、分级策略 |

---

## 🛣️ 开发路线

### Phase 0 — MVP（当前）

- [x] 架构设计文档
- [x] API 接口定义（113 个接口）
- [x] 数据模型设计（7 个域）
- [x] 部署方案
- [ ] 后端服务实现
- [ ] 前端页面开发
- [ ] Docker Compose 编排

### Phase 1 — 单体 + Worker

- [ ] 异步任务 Worker 拆分
- [ ] 媒体生成异步队列
- [ ] 基础监控接入

### Phase 2 — 微服务化

- [ ] 按服务域独立部署
- [ ] K8s 集群迁移
- [ ] 分布式追踪

---

## 🤝 贡献指南

### 分支策略

| 分支 | 用途 | 部署 |
|------|------|------|
| `main` | 稳定版本 | staging → production（手动审批） |
| `dev` | 开发集成 | dev 环境（自动） |
| `feature/*` | 功能开发 | 仅 CI，不部署 |
| `hotfix/*` | 紧急修复 | 快速通道 staging → production |

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新增知识点向量检索接口
fix: 修复教材解析状态机转换异常
docs: 更新 API 接口文档
chore: 升级 FastAPI 到 0.110
```

### 代码规范

- Python: `ruff` (linting) + `black` (formatting) + `mypy` (type checking)
- TypeScript: `eslint` + `prettier`
- 所有 PR 需通过 CI 检查

---

## 📄 许可证

[MIT](LICENSE)

---

<p align="center">
  <sub>知趣课堂 — 让学习更有趣 🎓</sub>
</p>
