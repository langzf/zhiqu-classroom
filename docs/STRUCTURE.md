# 项目文档结构（MVP）

> 最后更新: 2026-03-26
> 参考: [MVP-SCOPE.md](MVP-SCOPE.md) 了解功能边界

---

## 目录树

```
zhiqu-classroom/
├── docs/
│   ├── MVP-SCOPE.md                    # MVP 范围定义（5 大核心功能）
│   ├── STRUCTURE.md                    # ← 本文件
│   ├── tech-stack.md                   # 技术选型
│   │
│   ├── architecture/                   # 架构设计
│   │   ├── README.md                   # 架构索引
│   │   ├── system-overview.md          # 系统总览（分层、模块拓扑）
│   │   ├── service-detail.md           # 服务详细设计（4 个 MVP 模块）
│   │   ├── data-flow.md               # 核心数据流
│   │   └── deployment.md              # 部署方案（MVP 单机）
│   │
│   ├── api/                            # API 接口文档
│   │   ├── README.md                   # API 全局约定
│   │   ├── user-auth.md               # 认证 & 用户管理
│   │   ├── content-engine.md          # 教材 & 知识点
│   │   ├── learning-orchestrator.md   # 学习任务（简化版）
│   │   └── ai-tutor/                   # AI 辅导
│   │       ├── README.md
│   │       ├── conversations.md       # 对话管理
│   │       ├── messages.md            # 消息交互
│   │       └── ai-behavior.md         # AI 行为配置
│   │
│   ├── data-model/                     # 数据模型
│   │   ├── README.md                   # 数据模型索引 + 全局约定
│   │   ├── user-profile.md            # 用户域（4 表）
│   │   ├── course.md                   # 教材域（6 表）
│   │   └── ai-tutor.md               # AI 辅导域（2 表）
│   │
│   └── archive/                        # 归档（非 MVP，随时可恢复）
│       ├── README.md
│       ├── api/                        # 归档的 API 文档
│       ├── data-model/                 # 归档的数据模型
│       ├── frontend/                   # 归档的前端设计
│       ├── logging/                    # 归档的日志设计（12 子模块）
│       └── platform/                   # 归档的平台支撑（8 子模块）
│
├── services/                           # 后端（模块化单体）
│   ├── user-profile/                  # 用户模块
│   ├── content-engine/                # 内容引擎
│   ├── learning-core/                 # 学习核心（简化版）
│   ├── ai-tutor/                      # AI 辅导
│   └── shared/                        # 共享库
│
├── admin/                              # 管理后台（React）
├── app/                                # 学生端 H5（React）
├── miniapp/                            # 家长端小程序（Taro）— 后期
├── infra/                              # 基础设施配置
└── scripts/                            # 工具脚本
```

---

## 文档状态

### 架构设计 (`architecture/`)

| 文档 | 状态 | 说明 |
|------|------|------|
| system-overview.md | ✅ 完成 | 系统分层、模块拓扑 |
| service-detail.md | 🔧 需更新 | 从 8 服务精简到 4 模块 |
| data-flow.md | 🔧 需更新 | 保留 MVP 核心数据流 |
| deployment.md | 🔧 需更新 | 简化为单机部署 |

### API 接口 (`api/`)

| 文档 | 状态 | 说明 |
|------|------|------|
| user-auth.md | ✅ 完成 | 认证 + 用户管理 |
| content-engine.md | ✅ 完成 | 教材上传、解析、知识点 |
| learning-orchestrator.md | 🔧 需精简 | 砍掉自适应推荐部分 |
| ai-tutor/ | ✅ 完成 | 对话 + 消息 + AI 行为 |

### 数据模型 (`data-model/`)

| 文档 | 状态 | 表数 |
|------|------|------|
| user-profile.md | ✅ 完成 | 4 表 |
| course.md | ✅ 完成 | 6 表 |
| ai-tutor.md | ✅ 完成 | 2 表 |

### 归档内容 (`archive/`)

| 归档模块 | 恢复优先级 | 说明 |
|---------|-----------|------|
| analytics API + 数据模型 | P1（第二期） | 学情分析、报告 |
| admin API | P1（第二期） | 管理后台接口 |
| learning-engine 数据模型 | P1（第二期） | 完整学习引擎 |
| platform 支撑 | P1（第二期） | 审计、通知、配置中心 |
| media-generation API | P2 | 视频/动画/语音 |
| llm-ops 数据模型 | P2 | LLM 运维 |
| frontend 页面规格 | 按需 | 50+ 页面设计 |
| logging 设计 | P2 | 完整可观测性 |

---

## 命名约定

- **目录名**：`kebab-case`
- **文件名**：`kebab-case.md`
- **服务名**：与目录名一致
- **Schema 名**：`snake_case`
- **API 路径**：`/api/v1/{service}/{resource}`

## 文档间引用

架构 → API → 数据模型（自顶向下）。归档文件不应被新文档引用。
