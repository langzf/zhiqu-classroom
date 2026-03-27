# 学生端 H5 开发规范 (app)

> 适用于 `app/` 学生端 H5 应用  
> 技术栈：React 18 · TypeScript 5 · Vite · Zustand · React Router  
> 最后更新：2026-03-25

---

## 目录

1. [项目结构](#1-项目结构)
2. [TypeScript 编码规范](#2-typescript-编码规范)
3. [React 组件规范](#3-react-组件规范)
4. [状态管理](#4-状态管理)
5. [API 请求层](#5-api-请求层)
6. [样式规范](#6-样式规范)
7. [日志与错误处理](#7-日志与错误处理)
8. [测试规范](#8-测试规范)
9. [性能规范](#9-性能规范)
10. [Git 与协作](#10-git-与协作)

---

## 1. 项目结构

```
app/
├── public/                    # 静态资源
├── src/
│   ├── api/                   # API 请求层
│   │   ├── client.ts          #   Axios 实例、拦截器
│   │   ├── content.ts         #   教材/知识点 API
│   │   ├── learning.ts        #   学习任务 API
│   │   ├── tutor.ts           #   AI 辅导 API
│   │   └── user.ts            #   用户/认证 API
│   ├── components/            # 通用 UI 组件
│   │   ├── ui/                #   基础组件（Button, Modal, ...）
│   │   ├── layout/            #   布局组件（Header, TabBar, ...）
│   │   └── business/          #   业务组件（TaskCard, KPTag, ...）
│   ├── hooks/                 # 自定义 Hooks
│   │   ├── useAuth.ts
│   │   ├── useTask.ts
│   │   └── useStreaming.ts    #   SSE/WebSocket Hook
│   ├── pages/                 # 页面（按路由组织）
│   │   ├── home/
│   │   ├── tasks/
│   │   ├── tutor/
│   │   ├── profile/
│   │   └── login/
│   ├── stores/                # Zustand stores
│   │   ├── authStore.ts
│   │   ├── taskStore.ts
│   │   └── tutorStore.ts
│   ├── styles/                # 全局样式
│   │   ├── variables.css      #   CSS 变量
│   │   ├── reset.css          #   样式重置
│   │   └── global.css
│   ├── types/                 # 类型定义
│   ├── utils/                 # 工具函数
│   ├── constants/             # 常量、枚举
│   ├── router/                # 路由配置
│   │   └── index.tsx
│   ├── App.tsx
│   └── main.tsx
├── .env.development
├── .env.production
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── DEV-GUIDE.md               # 本文件
└── README.md
```

### 1.1 命名约定

| 类型 | 规范 | 示例 |
|------|------|------|
| 页面目录 | kebab-case | `pages/task-detail/` |
| 组件文件 | PascalCase | `TaskCard.tsx` |
| 非组件文件 | camelCase | `authStore.ts`, `useAuth.ts` |
| 样式文件 | 与组件同名 | `TaskCard.module.css` |
| 常量 | UPPER_SNAKE | `MAX_RETRY = 3` |

---

## 2. TypeScript 编码规范

### 2.1 基础配置

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "paths": {
      "@/*": ["./src/*"],
      "@zhiqu/shared": ["../packages/shared/src"]
    }
  }
}
```

### 2.2 类型定义

```typescript
// ✅ 优先 interface 定义对象类型
interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  dueAt: string;
  knowledgePoints: KnowledgePoint[];
}

// ✅ 枚举使用字面量联合类型
type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'expired';
type Subject = 'math' | 'chinese' | 'english' | 'physics' | 'chemistry';

// ✅ API 响应类型
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  request_id: string;
}

// ❌ 禁止使用 any，必要时用 unknown + 类型收窄
```

### 2.3 严格规则

- 开启 `strict: true`
- 禁止 `@ts-ignore`，可用 `@ts-expect-error`（附注释）
- 禁止无校验的 `as` 断言

---

## 3. React 组件规范

### 3.1 组件编写

```tsx
// ✅ 函数组件 + 命名导出
interface TaskCardProps {
  task: Task;
  onStart?: (taskId: string) => void;
}

export function TaskCard({ task, onStart }: TaskCardProps) {
  const handleStart = useCallback(() => {
    onStart?.(task.id);
  }, [task.id, onStart]);

  return (
    <div className={styles.card}>
      <h3>{task.title}</h3>
      <StatusBadge status={task.status} />
      {task.status === 'pending' && (
        <Button onClick={handleStart}>开始学习</Button>
      )}
    </div>
  );
}

// ❌ 不用 React.FC / class 组件 / 默认导出
```

### 3.2 Hooks 规范

```typescript
// ✅ use 前缀，返回明确类型
export function useTask(taskId: string) {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    taskApi.getById(taskId)
      .then(res => { if (!cancelled) setTask(res.data); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [taskId]);

  return { task, loading, error } as const;
}
```

### 3.3 拆分原则

- **超过 200 行**必须拆分
- 可复用逻辑 → 自定义 Hook
- UI 片段 → 子组件
- 页面组件只做布局 + 数据编排

---

## 4. 状态管理

### 4.1 状态分层

| 层级 | 工具 | 场景 |
|------|------|------|
| 服务端状态 | React Query / SWR | API 数据缓存、自动重试 |
| 全局状态 | Zustand | 认证、用户偏好 |
| 页面状态 | useState | 表单、UI 交互 |
| URL 状态 | React Router | 筛选、分页、Tab |

### 4.2 Zustand Store 示例

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  login: (token: string, user: UserProfile) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set) => ({
        token: null,
        user: null,
        login: (token, user) => set({ token, user }),
        logout: () => set({ token: null, user: null }),
      }),
      { name: 'zhiqu-auth' },
    ),
  ),
);
```

---

## 5. API 请求层

### 5.1 Axios 实例

```typescript
// api/client.ts
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30_000,    // 常规 30s
});

// 请求拦截：Token + Request-ID
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  config.headers['X-Request-ID'] = crypto.randomUUID();
  return config;
});

// 响应拦截：401 自动刷新 Token
client.interceptors.response.use(
  (res) => res.data,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshed = await tryRefreshToken();
      if (refreshed) return client.request(error.config);
      useAuthStore.getState().logout();
    }
    return Promise.reject(normalizeError(error));
  },
);
```

### 5.2 LLM 场景超时

AI 对话相关请求使用独立配置：

```typescript
const llmClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 120_000,   // LLM 场景 120s
});
```

### 5.3 SSE 流式

```typescript
// AI 辅导使用 Server-Sent Events
// 断线自动重连（最多 3 次，指数退避）
// 消息去重（基于 event_id）
```

---

## 6. 样式规范

### 6.1 方案

- **CSS Modules**（默认），组件级隔离
- **CSS 变量** 管理主题
- **postcss-px-to-viewport** 移动端适配（基准 375px）

### 6.2 设计令牌

```css
:root {
  --color-primary: #4F46E5;
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-text-primary: #1F2937;
  --color-text-secondary: #6B7280;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --font-size-sm: 14px;
  --font-size-md: 16px;
}
```

### 6.3 移动端适配

- 设计稿基准：375px
- 安全区域：`env(safe-area-inset-bottom)`
- 最大内容宽度：768px（平板居中）
- 触摸区域：最小 44×44px

---

## 7. 日志与错误处理

### 7.1 前端日志

```typescript
// utils/logger.ts
const LOG_LEVEL = import.meta.env.PROD ? 'warn' : 'debug';

export const logger = {
  debug: (...args: unknown[]) =>
    LOG_LEVEL === 'debug' && console.debug('[ZQ:DEBUG]', ...args),
  info: (...args: unknown[]) =>
    console.info('[ZQ:INFO]', ...args),
  warn: (...args: unknown[]) =>
    console.warn('[ZQ:WARN]', ...args),
  error: (...args: unknown[]) => {
    console.error('[ZQ:ERROR]', ...args);
    if (import.meta.env.PROD) reportToSentry(args);
  },
};
```

### 7.2 日志规则

| 级别 | 场景 | 生产环境 |
|------|------|----------|
| debug | 组件渲染、状态变化 | 关闭 |
| info | 页面导航、API 调用 | 保留 |
| warn | 非致命异常、降级 | 保留 + 上报 |
| error | 未捕获异常、API 失败 | 上报 Sentry |

### 7.3 全局错误边界

```tsx
export function ErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ReactErrorBoundary
      fallbackRender={({ error, resetErrorBoundary }) => (
        <ErrorPage error={error} onRetry={resetErrorBoundary} />
      )}
      onError={(error, info) => {
        logger.error('Uncaught error', error, info.componentStack);
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}
```

### 7.4 敏感信息

- 日志中 **禁止** 出现 Token、手机号明文
- 上报到 Sentry 时自动脱敏 `Authorization` header

---

## 8. 测试规范

### 8.1 工具链

| 工具 | 用途 |
|------|------|
| Vitest | 单元测试 |
| React Testing Library | 组件测试 |
| MSW | API Mock |
| Playwright | E2E 测试 |

### 8.2 测试结构

```
src/
├── components/
│   └── TaskCard/
│       ├── TaskCard.tsx
│       ├── TaskCard.module.css
│       └── TaskCard.test.tsx    # 就近放置
├── hooks/
│   └── __tests__/
│       └── useTask.test.ts
└── e2e/                         # E2E 测试
    └── login.spec.ts
```

### 8.3 覆盖率

| 层 | 最低覆盖率 |
|----|-----------|
| 工具函数 | 90% |
| 自定义 Hooks | 80% |
| 业务组件 | 70% |
| 页面组件 | 60%（E2E 覆盖核心路径） |

---

## 9. 性能规范

### 9.1 打包优化

- **代码分割**：路由级 `React.lazy()` + `Suspense`
- **Tree Shaking**：仅按需导入（`import { Button } from 'antd-mobile'`）
- **图片**：WebP 优先，懒加载（`loading="lazy"`）
- **字体**：仅加载中文常用子集

### 9.2 运行时

- **虚拟列表**：长列表（>50 项）使用 `react-virtuoso`
- **防抖/节流**：搜索输入 300ms 防抖，滚动事件 100ms 节流
- **Memo**：`React.memo()` 用于渲染开销大的纯展示组件
- **避免不必要渲染**：Zustand selector 精确选取

### 9.3 性能指标

| 指标 | 目标 |
|------|------|
| FCP | < 1.5s |
| LCP | < 2.5s |
| TTI | < 3.5s |
| Bundle (gzip) | < 200KB（首屏） |

---

## 10. Git 与协作

### 10.1 Commit 规范

```
feat(app): add AI tutor chat page
fix(app): fix token refresh loop
style(app): adjust task card spacing
```

### 10.2 代码格式化

```bash
# ESLint + Prettier（提交前自动运行）
pnpm lint        # 检查
pnpm lint:fix    # 自动修复
pnpm format      # Prettier 格式化
```

工具配置：

| 工具 | 用途 |
|------|------|
| ESLint | 代码质量 |
| Prettier | 代码格式 |
| husky | Git hooks |
| lint-staged | 仅检查暂存文件 |

### 10.3 PR 检查清单

- [ ] TypeScript 无报错
- [ ] ESLint 无警告
- [ ] 新组件有对应测试
- [ ] 移动端适配已验证（375px / 414px）
- [ ] 无硬编码文案（国际化预留）
- [ ] 无 console.log 遗留（使用 logger）
- [ ] Bundle size 无异常增长

---

## 附录：环境变量

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_SENTRY_DSN=

# .env.production
VITE_API_BASE_URL=https://api.zhiqu.com
VITE_WS_URL=wss://api.zhiqu.com/ws
VITE_SENTRY_DSN=https://xxx@sentry.io/xxx
```

---

*本文件为学生端 H5 开发规范。管理后台和家长端小程序另见各自 DEV-GUIDE.md。*