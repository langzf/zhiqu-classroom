# 前端开发计划 (TASK-FRONTEND-PLAN)

> 基于后端 API 现状 + 设计文档，制定 MVP 前端开发路线图

---

## 一、现状评估

### 后端 API 就绪状态

| 模块 | 前缀 | e2e 测试 | 状态 |
|------|------|----------|------|
| 用户认证 | `/api/v1/users` | 未测 | ⚠️ 代码存在，需验证 |
| 内容引擎 | `/api/v1/content` | 5/5 ✅ | ✅ 可用 |
| AI 辅导 | `/api/v1/tutor` | 8/8 ✅ | ✅ 可用 |
| 学习编排 | `/api/v1/learning` | 未测 | ⚠️ 代码存在，需验证 |
| 练习题生成 | `/api/v1/content/exercises` | 未测 | ⚠️ 端点已写，需验证 |

### 后端 API 清单

**用户认证** (`/api/v1/users`)
- `POST /register` — 手机号注册
- `POST /login` — 手机号登录（MVP 跳过验证码）
- `POST /refresh` — 刷新 token
- `GET /me` — 当前用户信息
- `PATCH /me` — 更新个人信息

**内容引擎** (`/api/v1/content`)
- `POST /textbooks` — 创建教材
- `POST /textbooks/upload` — 上传并解析教材
- `GET /textbooks` — 教材列表
- `GET /textbooks/{id}` — 教材详情
- `PATCH /textbooks/{id}` — 更新教材（admin）
- `POST /textbooks/{id}/parse` — 触发解析（admin）
- `GET /textbooks/{id}/chapters` — 章节树
- `GET /chapters/{id}/knowledge-points` — 知识点列表
- `POST /knowledge-points/search` — 知识点搜索
- `GET /knowledge-points/{id}/resources` — 知识点生成资源
- `POST /exercises/generate` — 生成练习题
- `GET /exercises/{resource_id}` — 获取练习题
- `GET /exercises` — 练习题列表
- Prompt 模板管理 CRUD（admin）

**AI 辅导** (`/api/v1/tutor`)
- `POST /conversations` — 创建会话
- `GET /conversations` — 会话列表
- `GET /conversations/{id}` — 会话详情
- `PATCH /conversations/{id}` — 更新会话
- `POST /conversations/{id}/archive` — 归档
- `DELETE /conversations/{id}` — 软删除
- `GET /conversations/{id}/messages` — 消息列表
- `POST /conversations/{id}/messages` — 发送消息（含 AI 回复）
- `POST /messages/{id}/feedback` — 消息反馈

**学习编排** (`/api/v1/learning`)
- 管理端：任务 CRUD + 发布/归档 + 子项管理
- 学生端：任务列表 + 开始/提交 + 进度查询

### 前端现状

三个前端项目均已有 **脚手架**（package.json + README），但 **无实际源码**：

| 项目 | 路径 | 技术栈 | 目标用户 | 状态 |
|------|------|--------|----------|------|
| `app/` | 学生 H5 | Vue 3 + Vant 4 + Pinia | 学生 | 仅骨架 |
| `admin/` | 管理后台 | Vue 3 + Element Plus + Pinia | 教师/管理员 | 仅骨架 |
| `miniapp/` | 家长小程序 | uni-app (Vue 3) | 家长 | 仅骨架 |
| `packages/shared/` | 共享包 | TypeScript | — | 仅骨架 |

---

## 二、MVP 前端范围裁剪

参照后端 MVP 精神 —— **砍到能用**。

### MVP 只做两个端：`admin` + `app`

| 优先级 | 项目 | 理由 |
|--------|------|------|
| **P0** | `admin/`（管理后台） | 没有管理后台就无法上传教材、创建任务 |
| **P0** | `app/`（学生 H5） | 学生端是核心体验 |
| **P2 延后** | `miniapp/`（家长小程序） | MVP 阶段家长端非必须，延后 |

### Admin 后台 — MVP 页面

| 页面 | 对应 API | 优先级 |
|------|----------|--------|
| 登录页 | `POST /login` | P0 |
| 教材管理 — 列表 + 上传 | `GET/POST /textbooks`, `/upload` | P0 |
| 教材详情 — 章节树 + 知识点 | `GET /chapters`, `/knowledge-points` | P0 |
| 练习题生成 | `POST /exercises/generate`, `GET /exercises` | P1 |
| 学习任务管理 | 任务 CRUD + 发布 | P1 |
| ~~用户管理~~ | — | MVP 不做 |
| ~~Prompt 模板管理~~ | — | MVP 不做（用默认模板） |
| ~~数据统计~~ | — | MVP 不做 |

### 学生 H5 — MVP 页面

| 页面 | 对应 API | 优先级 |
|------|----------|--------|
| 登录/注册 | `POST /login`, `/register` | P0 |
| 首页（任务列表） | `GET /student/tasks` | P0 |
| 教材浏览 — 章节 + 知识点 | `GET /chapters`, `/knowledge-points` | P0 |
| AI 对话页 | 会话 CRUD + 消息收发 | P0 |
| 练习题页 | `GET /exercises`, 答题交互 | P1 |
| 我的进度 | `GET /student/progress` | P1 |
| 个人中心 | `GET/PATCH /me` | P2 |

---

## 三、技术方案

### 共享包 `packages/shared/`

先建好共享层，两个前端项目复用：

```
packages/shared/
├── src/
│   ├── api/              # API 客户端（axios 封装）
│   │   ├── client.ts     # axios 实例 + 拦截器（token 注入、401 跳转、响应解包）
│   │   ├── auth.ts       # 认证 API
│   │   ├── content.ts    # 内容引擎 API
│   │   ├── tutor.ts      # AI 辅导 API
│   │   ├── learning.ts   # 学习编排 API
│   │   └── index.ts
│   ├── types/            # TypeScript 类型定义（对齐后端 schema）
│   │   ├── auth.ts
│   │   ├── content.ts
│   │   ├── tutor.ts
│   │   ├── learning.ts
│   │   └── common.ts     # PagedResponse, ApiResponse 等
│   ├── stores/           # Pinia stores（可选复用）
│   │   └── auth.ts       # token 管理、登录状态
│   ├── utils/
│   │   ├── token.ts      # JWT 存储/刷新
│   │   └── format.ts     # 日期/文件大小格式化
│   └── index.ts
├── package.json
└── tsconfig.json
```

### Admin 后台 `admin/`

```
admin/src/
├── App.vue
├── main.ts
├── router/
│   └── index.ts          # 路由定义 + 导航守卫
├── layouts/
│   └── DefaultLayout.vue # 侧边栏 + 顶栏
├── views/
│   ├── login/
│   │   └── LoginView.vue
│   ├── textbook/
│   │   ├── TextbookList.vue      # 教材列表 + 上传按钮
│   │   └── TextbookDetail.vue    # 章节树 + 知识点 + 练习题生成
│   ├── exercise/
│   │   └── ExercisePanel.vue     # 练习题生成面板（嵌入教材详情或独立）
│   └── task/
│       ├── TaskList.vue          # 任务列表
│       └── TaskEdit.vue          # 创建/编辑任务
├── components/
│   ├── ChapterTree.vue           # 章节树组件
│   ├── KnowledgePointCard.vue    # 知识点卡片
│   └── FileUpload.vue            # 教材上传组件
└── styles/
    └── variables.scss
```

### 学生 H5 `app/`

```
app/src/
├── App.vue
├── main.ts
├── router/
│   └── index.ts
├── layouts/
│   └── TabLayout.vue     # 底部 Tab 栏
├── views/
│   ├── login/
│   │   └── LoginView.vue
│   ├── home/
│   │   └── HomeView.vue          # 首页（任务卡片列表）
│   ├── textbook/
│   │   ├── TextbookList.vue      # 教材列表
│   │   ├── ChapterView.vue       # 章节 → 知识点
│   │   └── KnowledgeDetail.vue   # 知识点详情
│   ├── tutor/
│   │   ├── ChatList.vue          # 会话列表
│   │   └── ChatView.vue          # 对话界面（核心页）
│   ├── exercise/
│   │   └── ExerciseView.vue      # 答题页
│   └── profile/
│       └── ProfileView.vue       # 个人中心
├── components/
│   ├── ChatBubble.vue            # 消息气泡
│   ├── TaskCard.vue              # 任务卡片
│   └── NavBar.vue                # 顶部导航
└── styles/
    └── variables.scss
```

---

## 四、开发顺序（按 Sprint）

### Sprint 1：基础设施 + 登录（2-3 天）

**目标：** 两个前端跑起来，能登录

| # | 任务 | 项目 | 预估 |
|---|------|------|------|
| 1.1 | `packages/shared` — API client + types + token 工具 | shared | 0.5d |
| 1.2 | `admin/` — Vite + Vue3 + Element Plus 脚手架初始化 | admin | 0.5d |
| 1.3 | `admin/` — 登录页 + 路由守卫 + Layout | admin | 0.5d |
| 1.4 | `app/` — Vite + Vue3 + Vant4 脚手架初始化 | app | 0.5d |
| 1.5 | `app/` — 登录/注册页 + Tab Layout | app | 0.5d |
| 1.6 | 联调登录 API + token 刷新 | both | 0.5d |

### Sprint 2：内容管理 — Admin（2 天）

**目标：** 管理员能上传教材、看到解析结果

| # | 任务 | 项目 | 预估 |
|---|------|------|------|
| 2.1 | 教材列表页（表格 + 分页 + 筛选） | admin | 0.5d |
| 2.2 | 教材上传组件（拖拽 + 进度） | admin | 0.5d |
| 2.3 | 教材详情 — 章节树 + 知识点列表 | admin | 0.5d |
| 2.4 | 练习题生成面板（选知识点 → 生成 → 预览） | admin | 0.5d |

### Sprint 3：学生核心体验（2-3 天）

**目标：** 学生能浏览教材、和 AI 对话

| # | 任务 | 项目 | 预估 |
|---|------|------|------|
| 3.1 | 教材浏览 — 列表 → 章节 → 知识点 | app | 0.5d |
| 3.2 | AI 对话 — 会话列表 | app | 0.5d |
| 3.3 | AI 对话 — 聊天界面（消息收发 + 打字效果） | app | 1d |
| 3.4 | AI 对话 — 反馈（点赞/点踩） | app | 0.25d |

### Sprint 4：任务与练习（2 天）

**目标：** 完成任务流转闭环

| # | 任务 | 项目 | 预估 |
|---|------|------|------|
| 4.1 | Admin 任务管理 — 创建/编辑/发布 | admin | 1d |
| 4.2 | 学生首页 — 任务列表 + 开始/提交 | app | 0.5d |
| 4.3 | 学生练习页 — 答题交互 | app | 0.5d |

### Sprint 5：收尾打磨（1 天）

| # | 任务 | 项目 | 预估 |
|---|------|------|------|
| 5.1 | 学生个人中心 + 进度页 | app | 0.5d |
| 5.2 | 全局错误处理 + loading 状态 + 空状态 | both | 0.25d |
| 5.3 | 响应式适配检查 | both | 0.25d |

**总计预估：约 9-11 天**

---

## 五、开发规范

### 统一约定

| 项 | 规范 |
|----|------|
| 包管理 | pnpm（已配置 workspace） |
| TypeScript | strict 模式 |
| 代码风格 | ESLint + Prettier（创建项目时配置） |
| CSS 方案 | Admin → Element Plus 变量覆盖；App → Vant 主题定制 |
| API 响应格式 | `{ code: 0, data: ..., message: "" }` / `{ code: 0, data: { items, total, page, page_size } }` |
| 路由守卫 | 未登录 → 重定向 `/login`；token 过期 → 自动 refresh → 失败则登出 |
| 环境变量 | `VITE_API_BASE_URL`（默认 `http://localhost:8002`） |

### API Client 封装要点

```typescript
// packages/shared/src/api/client.ts
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002',
  timeout: 30000,
})

// 请求拦截：注入 Bearer token
// 响应拦截：解包 { code, data, message }，非 0 抛错，401 触发 refresh/logout
```

### 后端响应格式对齐

```typescript
// 标准响应
interface ApiResponse<T> {
  code: number      // 0 = 成功
  data: T
  message: string
}

// 分页响应
interface PagedResponse<T> {
  code: number
  data: {
    items: T[]
    total: number
    page: number
    page_size: number
  }
  message: string
}
```

---

## 六、前置条件检查

开始编码前需确认：

- [x] 后端服务可启动（端口 8002）
- [x] Content Engine API 通过 e2e 测试
- [x] AI Tutor API 通过 e2e 测试
- [ ] User Auth API 通过 e2e 测试（**需先验证！**）
- [ ] Learning Orchestrator API 通过 e2e 测试（Sprint 4 前验证即可）
- [ ] pnpm install 正常运行
- [ ] 两个前端项目 `dev` 命令可启动

---

## 七、建议执行方式

1. **先验证 User Auth API** — 前端所有页面都依赖登录，这是第一优先级
2. **Sprint 1 从 `packages/shared` 开始** — API client + types 是公共基础
3. **Admin 和 App 可并行开发** — 共享 API 层后，两个项目互不阻塞
4. **每个 Sprint 结束做一次全链路联调** — 避免最后集成爆炸

---

*创建时间：2026-03-27 19:47*
*状态：待确认后开始执行*