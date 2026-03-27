# 知趣课堂 MVP 范围定义

> 地基框架水电按正规来，第一期只装修必要的房间。

## 核心原则

- **架构骨架完整保留**：分层设计、模块边界、扩展点、接口契约
- **功能面收窄到 5 个核心**：只实现 MVP 必须的功能
- **部署极简**：单进程 FastAPI + 单 PostgreSQL + Redis，不搞微服务
- **归档不删除**：砍掉的文档在 `docs/archive/`，随时可捡回来

## MVP 5 大核心功能

### 1. 📚 教材上传与知识点抽取
- 管理员上传教材 PDF/DOCX
- 异步解析文档 → 提取章节目录树（≤4 层）
- LLM 辅助抽取知识点，向量化存入 pgvector
- **不做**：PPT 解析、OCR 扫描件、多版本教材对比

### 2. 📝 AI 生成练习题
- 基于知识点自动生成选择题、填空题
- 支持难度 1-5 级
- Prompt 模板可配置
- **不做**：小游戏（选择闯关、拖拽配对）、短视频脚本、动画

### 3. 🤖 AI 辅导对话
- 苏格拉底式引导对话（不直接给答案）
- 支持场景：自由提问、作业辅导、概念讲解
- 对话历史持久化
- 知识点 RAG 检索增强
- **不做**：复习引导、错题分析、多轮复杂推理链

### 4. 📋 学习任务与进度追踪
- 管理员/教师发布学习任务（关联章节 + 知识点）
- 学生领取任务、完成练习题、与 AI 对话
- 记录学习进度（完成率、正确率）
- **不做**：自适应推荐、学习路径规划、记忆曲线复习

### 5. 👨‍👩‍👧 用户体系与家长查看
- 手机号验证码登录 / 微信登录
- 三种角色：student / guardian / admin
- 家长绑定学生，只读查看学习进度
- **不做**：班级管理、教师角色、权限细分

## MVP 不做清单（已归档）

| 模块 | 归档内容 | 恢复优先级 |
|------|---------|-----------|
| analytics | 学情分析、知识诊断、报告生成 | P1（第二期） |
| media-gen | 视频脚本生成、动画引擎、语音合成 | P2 |
| admin | 26 个管理接口 | P1（第二期） |
| llm-ops | LLM 路由、熔断、调用日志、用量统计 | P2 |
| platform | 异步任务管理、审计日志、通知中心、系统配置 | P1（第二期） |
| logging | 完整可观测性（12 个子模块） | P2 |
| frontend | 50+ 页面规格 | 按需恢复 |

## 服务模块（MVP 保留）

| 模块 | 职责 | MVP 表数量 |
|------|------|-----------|
| user-profile | 登录认证、用户管理、家长绑定 | 4 张 |
| content-engine | 教材上传、解析、知识点、向量化 | 6 张 |
| ai-tutor | AI 辅导对话、RAG 检索 | 2 张 |
| learning-core | 学习任务分配、进度记录 | 3 张（简化） |

**总计：~15 张表**（原设计 30+ 张）

## 技术栈（MVP）

| 层 | 选型 |
|----|------|
| 后端 | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存 | Redis 7 |
| 对象存储 | MinIO |
| LLM | DeepSeek-V3（主力）、Qwen-2.5（备选） |
| 文档解析 | PyMuPDF + pdfplumber + python-docx |
| 消息队列 | Redis Streams |

**不引入**：Kafka、RabbitMQ、Milvus、Temporal、Prometheus/Grafana 全套

## 部署架构（MVP）

```
单机部署:
  FastAPI (uvicorn) :8000
  PostgreSQL 16 + pgvector
  Redis 7
  MinIO
  Nginx (反向代理 + 静态资源)
```

## 目录结构（docs/ 精简后）

```
docs/
├── MVP-SCOPE.md          ← 本文件，MVP 边界定义
├── STRUCTURE.md           ← 文档索引
├── tech-stack.md          ← 技术栈选型
├── architecture/          ← 架构设计（4 文件）
├── api/                   ← API 规范（6 文件）
│   ├── user-auth.md
│   ├── content-engine.md
│   ├── learning-orchestrator.md
│   └── ai-tutor/         ← AI 辅导 API（4 文件）
├── data-model/            ← 数据模型（4 文件）
│   ├── user-profile.md
│   ├── course.md
│   └── ai-tutor.md
└── archive/               ← 归档（随时可恢复）
```
