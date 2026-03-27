# 知趣课堂 (zhiqu-classroom)

> AI 驱动的 K12 课后辅导平台 — 让每个孩子都有自己的 AI 老师

---

## 🎯 项目简介

知趣课堂是一个面向 K12 学生的智能课后辅导平台。教师上传教材后，系统自动解析知识点，AI 生成练习题并提供辅导对话，帮助学生在课后高效巩固学习。

### MVP 核心功能

| # | 功能 | 说明 |
|---|------|------|
| 1 | 📚 教材上传与知识点抽取 | 上传 PDF/DOCX → 解析章节结构 → LLM 抽取知识点 → 向量化 |
| 2 | 📝 AI 生成练习题 | 基于知识点生成选择题/填空题，支持难度 1-5 级 |
| 3 | 🤖 AI 辅导对话 | 苏格拉底式引导，RAG 检索增强，不直接给答案 |
| 4 | 📋 学习任务与进度 | 发布任务 → 学生完成 → 记录进度（完成率、正确率） |
| 5 | 👨‍👩‍👧 用户体系与家长查看 | 手机号/微信登录，家长绑定学生，只读查看进度 |

> 完整 MVP 边界定义见 [docs/MVP-SCOPE.md](docs/MVP-SCOPE.md)

### 用户角色

| 角色 | 入口 | 说明 |
|------|------|------|
| 学生 | H5 页面 (React) | 完成任务、做练习、AI 对话 |
| 家长 | 微信小程序 (Taro) | 查看学习进度 |
| 管理员 | 管理后台 (React) | 上传教材、发布任务 |

---

## 🏗️ 技术架构

**模块化单体**，MVP 单进程部署。按 Python package 划分模块边界，未来可拆微服务。

```
客户端 (H5 / 小程序 / 管理后台)
         │ HTTPS
         ▼
┌─────────────────────────────┐
│      FastAPI (:8000)        │  路由 · JWT · 限流 · CORS
│  ┌─────────────────────┐    │
│  │ user-profile         │    │  认证、用户、家长绑定
│  │ content-engine       │    │  教材解析、知识点、向量化
│  │ learning-core        │    │  任务分配、进度记录
│  │ ai-tutor             │    │  AI 对话、RAG 检索
│  └─────────────────────┘    │
└──────────┬──────────────────┘
     ┌─────┼──────┬──────────┐
     ▼     ▼      ▼          ▼
   PostgreSQL  Redis  MinIO  LLM API
   (pgvector)              (DeepSeek)
```

### 技术栈

| 层面 | 选型 |
|------|------|
| **后端** | Python 3.12 + FastAPI |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic |
| **数据库** | PostgreSQL 16 + pgvector |
| **缓存/队列** | Redis 7 (缓存 + Streams) |
| **对象存储** | MinIO (S3 兼容) |
| **LLM** | DeepSeek-V3（主力）/ Qwen-2.5（备选） |
| **文档解析** | PyMuPDF + pdfplumber + python-docx |
| **部署** | Docker Compose（单机） |

---

## 📁 项目结构

```
zhiqu-classroom/
├── docs/                     # 项目文档
│   ├── MVP-SCOPE.md          #   MVP 范围定义
│   ├── STRUCTURE.md          #   文档结构索引
│   ├── tech-stack.md         #   技术选型
│   ├── architecture/         #   架构设计（4 文件）
│   ├── api/                  #   API 接口（6 文件）
│   ├── data-model/           #   数据模型（3 域，~12 表）
│   └── archive/              #   归档文档（非 MVP，可恢复）
│
├── services/                 # 后端（模块化单体）
│   ├── user-profile/         #   用户模块
│   ├── content-engine/       #   内容引擎
│   ├── learning-core/        #   学习核心
│   ├── ai-tutor/             #   AI 辅导
│   └── shared/               #   共享库
│
├── app/                      # 学生端 H5 (React)
├── admin/                    # 管理后台 (React)
├── miniapp/                  # 家长端小程序 (Taro) — 后期
└── infra/                    # 基础设施 (docker-compose 等)
```

> 详细文档结构参见 [docs/STRUCTURE.md](docs/STRUCTURE.md)

---

## 🚀 快速开始

### 环境要求

- Docker 24+ & Docker Compose v2
- Python 3.12+（本地开发）
- Node.js 20+（前端开发）

### 本地启动

```bash
# 1. 克隆项目
git clone https://github.com/your-org/zhiqu-classroom.git
cd zhiqu-classroom

# 2. 复制环境变量
cp .env.example .env

# 3. 启动基础设施
docker compose up -d postgres redis minio

# 4. 初始化数据库
python -m scripts.init_db

# 5. 启动应用
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 6. 验证
curl http://localhost:8000/health
```

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 |
| `REDIS_URL` | Redis 连接串 |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | 对象存储 |
| `LLM_API_KEY` | LLM 服务 API Key |
| `LLM_MODEL` | 默认模型 (deepseek-v3) |
| `JWT_SECRET` | JWT 签名密钥 |

---

## 📖 文档导航

| 文档 | 说明 |
|------|------|
| [MVP 范围](docs/MVP-SCOPE.md) | 5 大核心功能、不做清单 |
| [系统架构](docs/architecture/system-overview.md) | 分层设计、模块拓扑 |
| [服务设计](docs/architecture/service-detail.md) | 4 个模块的职责与接口 |
| [数据模型](docs/data-model/README.md) | 3 域 ~12 张表的 DDL |
| [API 接口](docs/api/README.md) | MVP 核心接口定义 |
| [技术选型](docs/tech-stack.md) | 技术栈决策 |

---

## 🛣️ 开发路线

### Phase 0 — MVP（当前）

- [x] 架构设计 & MVP 范围定义
- [x] 核心 API 接口定义
- [x] 核心数据模型设计（~12 表）
- [ ] 后端模块化单体实现
- [ ] 学生端 H5 核心页面
- [ ] Docker Compose 编排

### Phase 1 — 功能扩展

- [ ] 管理后台完善
- [ ] 学情分析 & 报告
- [ ] 家长端小程序
- [ ] 完整可观测性

### Phase 2 — 规模化

- [ ] 微服务拆分
- [ ] K8s 部署
- [ ] 媒体内容生成（游戏、视频）

---

## 📄 许可证

[MIT](LICENSE)

---

<p align="center">
  <sub>知趣课堂 — 让学习更有趣 🎓</sub>
</p>
