# 前端设计文档

> 知趣课堂前端架构、技术规范与页面设计

---

## 文档索引

| 文档 | 说明 |
|------|------|
| **本文** | 全局架构、技术选型、共享规范 |
| [student-h5.md](student-h5.md) | 学生端 H5 — 页面设计、路由、交互 |
| [parent-miniapp.md](parent-miniapp.md) | 家长端微信小程序 — 页面设计、路由 |
| [admin-console.md](admin-console.md) | 管理后台 — 页面设计、权限、布局 |

---

## 1. 三端总览

```
                  ┌──────────────────────────────────┐
                  │        API Gateway (:8000)        │
                  │     JWT · 限流 · CORS · 路由       │
                  └──┬────────────┬────────────┬──────┘
                     │            │            │
              ┌──────▼──┐  ┌─────▼─────┐  ┌───▼───────┐
              │ 学生端   │  │ 家长端     │  │ 管理后台   │
              │ H5 (Web) │  │ 小程序     │  │ Web SPA   │
              │ React 18 │  │ Taro 3     │  │ React 18  │
              │ Mobile UI│  │ WeChat     │  │ Ant Design│
              └──────────┘  └───────────┘  └───────────┘
```

| 维度 | 学生端 H5 | 家长端小程序 | 管理后台 |
|------|-----------|-------------|----------|
| **框架** | React 18 + TypeScript | Taro 3 + React + TS | React 18 + TypeScript |
| **UI 库** | Ant Design Mobile 5 | Taro UI / NutUI | Ant Design 5 + ProComponents |
| **目标平台** | 移动浏览器 (iOS/Android) | 微信小程序 | 桌面浏览器 (Chrome/Edge/Safari) |
| **路由** | React Router 6 | Taro Router | React Router 6 |
| **状态管理** | Zustand | Zustand | Zustand |
| **构建工具** | Vite 5 | Taro CLI | Vite 5 |
| **游戏引擎** | Phaser 3 (互动游戏) | — | — |
| **部署形态** | 静态资源 (CDN) | 微信审核发布 | 静态资源 (CDN / Nginx) |

---

## 2. 全局技术规范

### 2.1 项目目录结构（通用模板）

```
src/
├── api/              # API 请求层（按服务域拆分）
│   ├── client.ts     #   axios 实例 + 拦截器
│   ├── auth.ts       #   认证相关
│   ├── content.ts    #   内容引擎
│   └── ...
├── components/       # 通用组件
├── hooks/            # 自定义 Hook
├── pages/            # 页面（按路由组织）
├── stores/           # Zustand store
├── utils/            # 工具函数
├── types/            # TypeScript 类型定义
├── styles/           # 全局样式 / 主题变量
└── constants/        # 枚举、常量
```

### 2.2 网络请求层

统一封装 HTTP Client，所有请求经由 `api/client.ts`：

```typescript
// api/client.ts
import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL, // https://api.zhiqu.com
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截：注入 JWT
client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截：统一错误处理 + 解包
client.interceptors.response.use(
  (res) => res.data,  // 解包 { code, message, data }
  async (error) => {
    if (error.response?.status === 401) {
      const refreshed = await tryRefreshToken();
      if (refreshed) return client(error.config);
      redirectToLogin();
    }
    return Promise.reject(normalizeError(error));
  }
);
```

**统一响应格式（与后端约定一致）：**

```typescript
interface ApiResponse<T = unknown> {
  code: number;         // 0 = 成功
  message: string;
  data: T;
  request_id: string;
}
```

### 2.3 认证流程

```
┌──────┐                    ┌───────────┐                ┌──────────┐
│ 客户端 │                   │ API GW    │                │ Redis    │
└──┬───┘                    └─────┬─────┘                └────┬─────┘
   │  POST /auth/sms/send        │                           │
   │  { phone }                  │──存验证码(5min TTL)───────►│
   │◄─────── 200 ────────────────│                           │
   │                             │                           │
   │  POST /auth/sms/login       │                           │
   │  { phone, code }           │──校验验证码────────────────►│
   │                             │  签发 JWT                  │
   │◄─── { access, refresh } ───│                           │
   │                             │                           │
   │  ─── 请求携带 Bearer ───►   │                           │
   │                             │                           │
   │  access_token 过期          │                           │
   │  POST /auth/token/refresh   │                           │
   │  { refresh_token }         │                           │
   │◄─── 新 { access, refresh } │                           │
```

**Token 存储策略：**

| 客户端 | access_token | refresh_token |
|--------|-------------|---------------|
| 学生端 H5 | 内存 (Zustand) | localStorage |
| 家长端小程序 | 内存 | wx.setStorageSync |
| 管理后台 | 内存 (Zustand) | httpOnly Cookie (首选) / localStorage |

> access_token 不持久化到 localStorage，刷新页面时用 refresh_token 静默续签。

### 2.4 状态管理

使用 **Zustand** — 轻量、TypeScript 友好、无 Provider 嵌套：

```typescript
// stores/auth.ts
interface AuthState {
  user: User | null;
  accessToken: string | null;
  login: (phone: string, code: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  login: async (phone, code) => {
    const { data } = await authApi.smsLogin({ phone, code });
    set({ user: data.user, accessToken: data.access_token });
    saveRefreshToken(data.refresh_token);
  },
  logout: () => {
    set({ user: null, accessToken: null });
    clearRefreshToken();
  },
  // ...
}));
```

**Store 拆分原则：**

| Store | 内容 | 持久化 |
|-------|------|--------|
| `authStore` | 用户信息、token | refresh_token 持久化 |
| `taskStore` | 学习任务列表、当前任务 | 否 |
| `chatStore` | AI 对话会话、消息列表 | 否 |
| `settingsStore` | 主题、字体大小等 | localStorage |

### 2.5 样式方案

| 客户端 | 方案 | 适配 |
|--------|------|------|
| 学生端 H5 | CSS Modules + CSS Variables | `postcss-px-to-viewport` (375px 基准) |
| 家长端小程序 | Taro CSS Modules | `pxtransform` (750rpx 设计稿) |
| 管理后台 | Ant Design 主题 Token + CSS Modules | 响应式（最小 1280px） |

**设计 Token（全局色彩）：**

```css
:root {
  --color-primary: #4F46E5;      /* 品牌主色 */
  --color-primary-light: #818CF8;
  --color-success: #10B981;      /* 正确/完成 */
  --color-warning: #F59E0B;      /* 警告/待处理 */
  --color-danger: #EF4444;       /* 错误/失败 */
  --color-bg: #F8FAFC;           /* 页面背景 */
  --color-card: #FFFFFF;
  --color-text: #1E293B;
  --color-text-secondary: #64748B;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
}
```

### 2.6 错误处理

```typescript
// 统一错误边界
<ErrorBoundary fallback={<ErrorPage />}>
  <App />
</ErrorBoundary>

// API 错误统一 toast
function normalizeError(error: AxiosError<ApiResponse>): AppError {
  const resp = error.response?.data;
  return {
    code: resp?.code ?? -1,
    message: resp?.message ?? '网络异常，请稍后重试',
    requestId: resp?.request_id,
  };
}
```

**常见错误码映射：**

| code | 含义 | 前端处理 |
|------|------|----------|
| 0 | 成功 | — |
| 401001 | token 过期 | 静默刷新 |
| 401002 | 无效 token | 跳登录页 |
| 403001 | 权限不足 | toast + 跳首页 |
| 404001 | 资源不存在 | 404 页面 |
| 429001 | 请求过频 | toast + 倒计时 |

### 2.7 性能优化策略

| 策略 | 说明 |
|------|------|
| **路由懒加载** | `React.lazy()` + `Suspense`，首屏只加载当前路由 |
| **图片懒加载** | `loading="lazy"` + IntersectionObserver |
| **请求缓存** | SWR / React Query 缓存 + 后台刷新 |
| **虚拟列表** | 长列表使用 `react-virtuoso` |
| **打包优化** | Vite 分包（vendor / antd / phaser 独立 chunk） |
| **CDN 加速** | 静态资源上传至 CDN，开启 Brotli 压缩 |
| **预加载** | 关键路由 `<link rel="prefetch">` |

---

## 3. 共享组件库

三端共享部分逻辑，抽取为内部包 `@zhiqu/shared`：

```
packages/shared/
├── types/            # 共享 TypeScript 类型
│   ├── api.ts        #   API 响应类型
│   ├── user.ts       #   用户模型
│   ├── task.ts       #   任务模型
│   └── enums.ts      #   枚举（学科、年级、角色等）
├── utils/            # 共享工具函数
│   ├── format.ts     #   日期/时间格式化
│   ├── validate.ts   #   手机号等校验
│   └── token.ts      #   JWT 解析
└── constants/        # 共享常量
    ├── subjects.ts   #   学科列表
    └── grades.ts     #   年级列表
```

**核心枚举定义：**

```typescript
// types/enums.ts
export enum Subject {
  Math = 'math', Chinese = 'chinese', English = 'english',
  Physics = 'physics', Chemistry = 'chemistry', Biology = 'biology',
  History = 'history', Geography = 'geography', Politics = 'politics',
}

export enum Grade {
  Grade1 = 'grade_1', /* ... */ Grade12 = 'grade_12',
}

export enum UserRole {
  Student = 'student', Parent = 'parent',
  Teacher = 'teacher', Admin = 'admin',
}

export enum TaskStatus {
  Draft = 'draft', Published = 'published', Archived = 'archived',
}

export enum AssignmentStatus {
  Assigned = 'assigned', InProgress = 'in_progress',
  Completed = 'completed', Expired = 'expired',
}
```

---

## 4. 开发环境

### 4.1 Monorepo 结构

```
zhiqu-classroom/
├── packages/shared/         # @zhiqu/shared
├── app/                     # 学生端 H5
├── admin/                   # 管理后台
├── miniapp/                 # 家长端小程序（对应现 services/ 外的前端）
├── pnpm-workspace.yaml
└── package.json
```

使用 **pnpm workspace** 管理：

```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
  - 'app'
  - 'admin'
  - 'miniapp'
```

### 4.2 开发 & 构建命令

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm --filter app dev          # 学生端 :3000
pnpm --filter admin dev        # 管理后台 :3001
pnpm --filter miniapp dev      # 小程序开发者工具

# 构建
pnpm --filter app build        # → app/dist/
pnpm --filter admin build      # → admin/dist/
pnpm --filter miniapp build    # → miniapp/dist/

# 代码检查
pnpm lint                      # 全量 lint
pnpm typecheck                 # TypeScript 类型检查
```

### 4.3 环境变量

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_WX_APP_ID=wxXXX

# .env.production
VITE_API_BASE_URL=https://api.zhiqu.com
VITE_WX_APP_ID=wxYYY
```

---

## 5. 部署策略

| 客户端 | 构建产物 | 部署方式 |
|--------|---------|----------|
| 学生端 H5 | `app/dist/` 静态文件 | CDN + Nginx，域名 `app.zhiqu.com` |
| 管理后台 | `admin/dist/` 静态文件 | CDN + Nginx，域名 `admin.zhiqu.com` |
| 家长端小程序 | `miniapp/dist/` | 微信开发者工具上传 → 审核发布 |

**Nginx 配置要点：**

```nginx
# SPA history fallback
location / {
    try_files $uri $uri/ /index.html;
}

# 静态资源长缓存
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

*最后更新：2026-03-25*