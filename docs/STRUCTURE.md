# 项目文档结构

> 最后更新: 2026-03-25

---

## 目录树

```
zhiqu-classroom/
├── docs/                               # 项目文档
│   ├── STRUCTURE.md                    # ← 本文件
│   ├── tech-stack.md                   # 技术选型与决策
│   ├── logging-design.md              # 日志设计（格式、脱敏、分级）
│   │
│   ├── architecture/                   # 架构设计
│   │   ├── README.md                   # 架构文档索引
│   │   ├── system-overview.md          # 系统总览（分层、服务拓扑、通信）
│   │   ├── service-detail.md           # 服务详细设计（8 个服务）
│   │   ├── data-flow.md               # 核心数据流（教材解析、互动生成等）
│   │   └── deployment.md              # 部署方案（容器编排、CI/CD、监控、运维）
│   │
│   ├── api/                            # API 接口文档
│   │   ├── README.md                   # API 模块索引 + 全局约定
│   │   ├── user-auth.md               # 认证 & 用户管理 (12 接口)
│   │   ├── content-engine.md          # 教材 & 知识点 (16 接口)
│   │   ├── media-generation.md        # 互动内容生成 (13 接口)
│   │   ├── learning-orchestrator.md   # 学习任务编排 (16 接口)
│   │   ├── analytics.md               # 数据分析 & 报告 (12 接口)
│   │   ├── admin.md                    # 管理后台 (26 接口)
│   │   └── ai-tutor/                   # AI 辅导（拆分目录）
│   │       ├── README.md               # AI 辅导接口索引
│   │       ├── conversations.md       # 对话管理 (8 接口)
│   │       ├── messages.md            # 消息交互 (5 接口)
│   │       └── knowledge.md           # 知识检索 (5 接口)
│   │
│   ├── data-model/                     # 数据模型（DDL + 索引 + 说明）
│   │   ├── README.md                   # 数据模型索引 + 全局约定
│   │   ├── user-profile.md            # 用户域 (users, student_profiles, guardian_bindings)
│   │   ├── course.md                   # 教材域 (textbooks, chapters, knowledge_points, ...)
│   │   ├── learning-engine.md         # 学习域 (tasks, submissions, learning_records, ...)
│   │   ├── ai-tutor.md                # AI辅导域 (conversations, messages)
│   │   ├── llm-ops.md                 # LLM运维域 (model_providers, call_logs, ...)
│   │   ├── analytics.md               # 分析域 (daily_study_stats, weekly_reports, ...)
│   │   └── platform/                   # 平台支撑域（拆分目录）
│   │       ├── README.md               # 平台支撑索引 (8 表总览)
│   │       ├── sys-configs.md         # 配置中心 (sys_configs, sys_config_history)
│   │       ├── audit-logs.md          # 审计日志 (audit_logs)
│   │       ├── async-tasks.md         # 异步任务 (async_tasks, async_task_logs)
│   │       └── notification.md        # 消息通知 (templates, logs, preferences)
│   │
│   └── archive/                        # 归档（已被取代的旧文件）
│       ├── README.md                   # 归档说明 + 替代对照表
│       ├── data-model.md              # ← 被 data-model/ 目录取代
│       ├── api-spec.md                # ← 被 api/ 目录取代
│       ├── ai-education-app-initial.md # ← 被 architecture/ 取代
│       └── platform-support.md        # ← 被 architecture/ + data-model/platform/ 取代
│
├── services/                           # 后端服务（模块化单体）
│   ├── README.md                       # 服务目录说明
│   ├── CONTRACTS.md                   # 服务间契约与事件定义
│   ├── api-gateway/                   # API 网关 (:8000)
│   ├── user-profile/                  # 用户服务 (:8001)
│   ├── content-engine/                # 内容引擎 (:8002)
│   ├── media-generation/              # 媒体生成 (:8003)
│   ├── learning-orchestrator/         # 学习编排 (:8005)
│   ├── analytics-reporting/           # 数据分析 (:8006)
│   ├── notification/                  # 通知服务 (:8007)
│   └── shared/                        # 共享库
│
├── admin/                              # 管理后台（React）
├── app/                                # 学生端 H5（React）
├── scripts/                            # 工具脚本
│   ├── api-spec-toc.ps1
│   ├── check-api.ps1
│   ├── dm-toc.ps1
│   ├── list-dm.ps1
│   ├── list-files.ps1
│   ├── toc.ps1
│   ├── verify-api.ps1
│   └── verify-lo.ps1
│
├── .gitignore
├── package.json
└── README.md
```

---

## 文档状态

### 架构设计 (`docs/architecture/`)

| 文档 | 状态 | 说明 |
|------|------|------|
| system-overview.md | ✅ 完成 | 系统分层、服务拓扑、通信机制 |
| service-detail.md | ✅ 完成 | 8 个服务的详细设计 |
| data-flow.md | ✅ 完成 | 5 条核心业务数据流 |
| deployment.md | ✅ 完成 | 部署方案（511 行） |

### API 接口 (`docs/api/`)

| 文档 | 状态 | 接口数 |
|------|------|--------|
| user-auth.md | ✅ 完成 | 12 |
| content-engine.md | ✅ 完成 | 16 |
| media-generation.md | ✅ 完成 | 13 |
| learning-orchestrator.md | ✅ 完成 | 16 |
| analytics.md | ✅ 完成 | 12 |
| admin.md | ✅ 完成 | 26 |
| ai-tutor/ | ✅ 完成 | 18 |
| **合计** | | **113** |

### 数据模型 (`docs/data-model/`)

| 文档 | 状态 | Schema |
|------|------|--------|
| user-profile.md | ✅ 完成 | user_profile |
| course.md | ✅ 完成 | content |
| learning-engine.md | ✅ 完成 | learning |
| ai-tutor.md | ✅ 完成 | tutor |
| llm-ops.md | ✅ 完成 | llm_ops |
| analytics.md | ✅ 完成 | analytics |
| platform/ | ✅ 完成 | platform + notification |

### 其他

| 文档 | 状态 | 说明 |
|------|------|------|
| tech-stack.md | ✅ 完成 | 技术选型决策 |
| logging-design.md | ✅ 完成 | 日志设计 |

---

## 待完成

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 项目 README.md | P1 | 项目简介、快速启动、贡献指南 |
| 前端设计文档 | P2 | 学生端 H5 + 管理后台 + 家长端小程序 |

---

## 命名约定

- **目录名**：`kebab-case`（如 `data-model/`、`api-gateway/`）
- **文件名**：`kebab-case.md`（如 `system-overview.md`）
- **服务名**：与目录名一致（如 `content-engine`）
- **Schema 名**：`snake_case`（如 `user_profile`、`llm_ops`）
- **接口路径**：`/api/v1/{service}/{resource}`

## 文档间引用

- 架构文档引用 → API 文档引用 → 数据模型（自顶向下）
- 数据模型之间通过"跨服务引用"表说明 UUID 关联
- 归档文件不应被新文档引用（仅供历史追溯）
