# 学生端 H5 — 页面设计

> 父文档：[README.md](README.md) | API 参考：[learning-orchestrator](../api/learning-orchestrator.md)、[ai-tutor](../api/ai-tutor.md)  
> 技术栈：React 18 + TypeScript + Vite 5 + Ant Design Mobile 5 + Phaser 3

---

## 1. 页面路由

| 路径 | 页面 | 认证 | 说明 |
|------|------|------|------|
| `/login` | 登录 | ✗ | 手机号验证码登录 |
| `/` | 首页 | ✓ | 今日任务 + 快捷入口 |
| `/tasks` | 任务列表 | ✓ | 全部学习任务 |
| `/tasks/:id` | 任务详情 | ✓ | 资源列表 + 开始学习 |
| `/learn/:resourceId` | 互动学习 | ✓ | 游戏/视频/练习 播放器 |
| `/chat` | AI 辅导 | ✓ | 对话列表 |
| `/chat/:sessionId` | 对话详情 | ✓ | AI 对话交互 |
| `/profile` | 个人中心 | ✓ | 学习档案 + 设置 |
| `/report` | 学习报告 | ✓ | 周报 + 知识点雷达图 |
| `/report/:id` | 报告详情 | ✓ | 单份报告完整内容 |

### 路由守卫

```typescript
function AuthGuard({ children }: { children: ReactNode }) {
  const { accessToken, refreshToken } = useAuthStore();

  if (!accessToken) {
    const refreshed = await refreshToken();
    if (!refreshed) return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <AuthGuard><AppLayout /></AuthGuard>,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'tasks', element: <TaskListPage /> },
      { path: 'tasks/:id', element: <TaskDetailPage /> },
      { path: 'learn/:resourceId', element: <LearnPage /> },
      { path: 'chat', element: <ChatListPage /> },
      { path: 'chat/:sessionId', element: <ChatPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'report', element: <ReportListPage /> },
      { path: 'report/:id', element: <ReportDetailPage /> },
    ],
  },
]);
```

---

## 2. 核心页面设计

### 2.1 登录页 `/login`

```
┌────────────────────────────┐
│        🎓 知趣课堂          │
│                            │
│  ┌──────────────────────┐  │
│  │ 📱 请输入手机号        │  │
│  └──────────────────────┘  │
│  ┌────────────┐ ┌───────┐  │
│  │ 验证码      │ │ 获取   │  │
│  └────────────┘ └───────┘  │
│                            │
│  ┌──────────────────────┐  │
│  │      登录 / 注册       │  │
│  └──────────────────────┘  │
│                            │
│      ── 其他登录方式 ──     │
│        [ 微信登录 ]        │
│   阅读并同意《用户协议》     │
└────────────────────────────┘
```

**交互要点：**
- 手机号实时校验（11 位数字）
- 获取验证码按钮 60s 倒计时
- 登录成功 → 跳转首页 `/`
- 微信登录 → 调用微信 OAuth → 首次需绑定手机号

**调用接口：**
- `POST /api/v1/auth/sms/send` — 发送验证码
- `POST /api/v1/auth/sms/login` — 验证码登录
- `POST /api/v1/auth/wx/login` — 微信登录

---

### 2.2 首页 `/`

```
┌────────────────────────────┐
│ 👋 你好，小明     [头像]     │
│ 三年级 · 数学               │
├────────────────────────────┤
│ 📋 今日任务 (2/5)           │
│ ┌────────────────────────┐ │
│ │ ✅ 分数的认识 - 游戏     │ │
│ │ ✅ 分数的认识 - 练习     │ │
│ │ 🔵 分数的比较 - 视频     │ │
│ │ ○  分数的比较 - 游戏     │ │
│ │ ○  分数的比较 - 练习     │ │
│ └────────────────────────┘ │
├────────────────────────────┤
│ 快捷入口                    │
│ ┌──────┐ ┌──────┐ ┌──────┐ │
│ │ 🤖   │ │ 📊   │ │ 📚   │ │
│ │AI辅导│ │学习报告│ │知识树 │ │
│ └──────┘ └──────┘ └──────┘ │
├────────────────────────────┤
│ 🏆 学习数据                 │
│ 连续学习 7 天  本周完成 12题 │
│ ████████░░ 80%              │
└────────────────────────────┘
│  🏠   │  📋   │  🤖  │ 👤  │  ← 底部 Tab
│  首页  │  任务  │ AI  │ 我的 │
```

**数据加载：**
- `GET /api/v1/assignments/mine?status=assigned,in_progress&due=today` — 今日任务
- `GET /api/v1/users/me/profile` — 用户信息
- `GET /api/v1/analytics/study-stats/mine` — 学习统计

**底部 TabBar：**

| Tab | 图标 | 路由 | Badge |
|-----|------|------|-------|
| 首页 | 🏠 | `/` | — |
| 任务 | 📋 | `/tasks` | 待完成数 |
| AI | 🤖 | `/chat` | — |
| 我的 | 👤 | `/profile` | — |

---

### 2.3 互动学习页 `/learn/:resourceId`

学生端最核心页面，根据资源类型渲染不同内容：

| 资源类型 | 渲染方式 | 交互 |
|----------|---------|------|
| `interactive_game` | Phaser 3 Canvas | 拖拽、点击、计时 |
| `exercise` | 题目卡片组件 | 选择、填空、判断 |
| `video_script` | 视频播放器 | 播放、暂停、进度 |
| `mind_map` | SVG / Canvas 渲染 | 缩放、展开折叠 |

```
┌────────────────────────────┐
│ ← 分数的认识        2/5 题  │
├────────────────────────────┤
│                            │
│    ┌────────────────────┐  │
│    │                    │  │
│    │   Phaser Canvas    │  │
│    │   (互动游戏区域)    │  │
│    │                    │  │
│    └────────────────────┘  │
│                            │
│  把 🍕 平均分给 3 个小朋友  │
│  每人分到几分之几？         │
│                            │
│  ┌─────┐ ┌─────┐ ┌─────┐  │
│  │ 1/2 │ │ 1/3 │ │ 1/4 │  │
│  └─────┘ └─────┘ └─────┘  │
│                            │
│        [提交答案]           │
│  💬 不懂？问问 AI 老师      │
└────────────────────────────┘
```

**Phaser 游戏集成：**

```typescript
// components/GamePlayer.tsx
function GamePlayer({ resourceId, gameConfig }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Phaser.Game | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    gameRef.current = new Phaser.Game({
      parent: containerRef.current,
      width: window.innerWidth,
      height: window.innerWidth * 0.75,
      scene: createScene(gameConfig),
      physics: { default: 'arcade' },
      scale: { mode: Phaser.Scale.FIT },
    });
    return () => { gameRef.current?.destroy(true); };
  }, [gameConfig]);

  return <div ref={containerRef} className={styles.gameContainer} />;
}
```

**学习记录上报（防丢失）：**

```typescript
// 使用 sendBeacon 确保页面关闭时数据不丢
const reportProgress = useDebouncedCallback(
  (data: ProgressData) => {
    navigator.sendBeacon('/api/v1/learning-records', JSON.stringify(data));
  },
  1000
);

useEffect(() => {
  const handleBeforeUnload = () => reportProgress.flush();
  window.addEventListener('beforeunload', handleBeforeUnload);
  return () => window.removeEventListener('beforeunload', handleBeforeUnload);
}, []);
```

**调用接口：**
- `GET /api/v1/resources/:id` — 资源详情 + 游戏配置
- `POST /api/v1/learning-records` — 上报学习记录
- `PATCH /api/v1/assignments/:id/progress` — 更新作业进度

---

### 2.4 AI 辅导对话 `/chat/:sessionId`

```
┌────────────────────────────┐
│ ← AI 辅导 · 分数的比较      │
├────────────────────────────┤
│                            │
│  ┌─────────────────────┐   │
│  │ 🤖 你好！我是你的 AI │   │
│  │ 辅导老师。关于分数的  │   │
│  │ 比较，你哪里不太明白？│   │
│  └─────────────────────┘   │
│                            │
│          ┌──────────────┐  │
│          │ 1/3 和 1/4   │  │
│          │ 哪个大？      │  │
│          └──────────────┘  │
│                            │
│  ┌─────────────────────┐   │
│  │ 🤖 好问题！我们来想  │   │
│  │ 一想：如果一个披萨分  │   │
│  │ 成3份和4份...        │   │
│  └─────────────────────┘   │
│                            │
│  推荐问题：                 │
│  ┌──────────┐ ┌─────────┐  │
│  │ 什么是通分 │ │举个例子  │  │
│  └──────────┘ └─────────┘  │
├────────────────────────────┤
│ [输入消息...]    [🎤] [📤] │
└────────────────────────────┘
```

**交互要点：**
- 消息支持 Markdown 渲染（数学公式用 KaTeX）
- 流式输出（SSE）：逐字显示 AI 回复
- 推荐问题：后端返回 `suggested_questions`
- 上下文绑定：对话关联当前知识点

**SSE 流式消息实现：**

```typescript
function useStreamChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);

  const sendMessage = async (content: string) => {
    setMessages(prev => [...prev, { role: 'user', content }]);
    setStreaming(true);

    const response = await fetch(
      `/api/v1/tutor/sessions/${sessionId}/messages`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAccessToken()}`,
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ content }),
      }
    );

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let assistantMsg = '';
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
      for (const line of lines) {
        const data = JSON.parse(line.slice(6));
        if (data.type === 'token') {
          assistantMsg += data.content;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: 'assistant', content: assistantMsg };
            return updated;
          });
        }
      }
    }
    setStreaming(false);
  };

  return { messages, sendMessage, streaming };
}
```

**调用接口：**
- `POST /api/v1/tutor/sessions` — 创建对话
- `POST /api/v1/tutor/sessions/:id/messages` — 发送消息（SSE）
- `GET /api/v1/tutor/sessions/:id/messages` — 历史消息

---

### 2.5 个人中心 `/profile`

```
┌────────────────────────────┐
│        [头像]               │
│        小明                 │
│    三年级 · 实验小学         │
├────────────────────────────┤
│ 📊 学习报告                 │ → /report
│ ⚙️  设置                    │ → 字体大小、通知
│ 📞 联系客服                 │
│ 🚪 退出登录                 │
└────────────────────────────┘
```

**调用接口：**
- `GET /api/v1/users/me` — 用户基本信息
- `GET /api/v1/users/me/profile` — 学生档案
- `PUT /api/v1/users/me/profile` — 更新档案

---

### 2.6 学习报告 `/report`

```
┌────────────────────────────┐
│ ← 学习报告                  │
├────────────────────────────┤
│ 📅 本周报告 (3.18 - 3.24)   │
│ ┌────────────────────────┐ │
│ │ 学习时长: 4.5h          │ │
│ │ 完成任务: 15/18         │ │
│ │ 正确率:   82%           │ │
│ └────────────────────────┘ │
│                            │
│ 🎯 知识点掌握度             │
│ ┌────────────────────────┐ │
│ │     (雷达图 / 柱状图)   │ │
│ │    ECharts Canvas       │ │
│ └────────────────────────┘ │
│                            │
│ ⚠️ 薄弱知识点               │
│ · 分数的比较 (60%)          │
│ · 分数的加减法 (55%)        │
│   [去练习 →]                │
│                            │
│ 历史报告                    │
│ · 3.11 - 3.17 周报 →       │
│ · 3.04 - 3.10 周报 →       │
└────────────────────────────┘
```

**图表方案：** 使用 ECharts（轻量 Canvas 渲染），按需引入雷达图和柱状图模块。

**调用接口：**
- `GET /api/v1/analytics/reports/mine?type=weekly` — 周报列表
- `GET /api/v1/analytics/reports/:id` — 报告详情
- `GET /api/v1/analytics/knowledge-mastery/mine` — 知识点掌握度

---

## 3. 组件设计

### 3.1 核心组件清单

| 组件 | 说明 | 使用页面 |
|------|------|----------|
| `TaskCard` | 任务卡片（状态标签 + 进度条） | 首页、任务列表 |
| `GamePlayer` | Phaser 3 游戏容器 | 互动学习 |
| `VideoPlayer` | 视频播放器（进度上报） | 互动学习 |
| `ExerciseCard` | 题目卡片（选择/填空/判断） | 互动学习 |
| `ChatBubble` | 聊天气泡（Markdown + KaTeX） | AI 辅导 |
| `StreamingText` | 流式文字动画 | AI 辅导 |
| `RadarChart` | 知识点雷达图 | 学习报告 |
| `ProgressRing` | 环形进度条 | 首页、任务详情 |
| `EmptyState` | 空状态插图 | 通用 |
| `LoadingSkeleton` | 骨架屏 | 通用 |

### 3.2 ChatBubble 组件

支持富文本渲染，关键实现：

```typescript
// components/ChatBubble.tsx
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn(styles.bubble, isUser ? styles.user : styles.assistant)}>
      {isUser ? (
        <p>{message.content}</p>
      ) : (
        <ReactMarkdown
          remarkPlugins={[remarkMath]}
          rehypePlugins={[rehypeKatex]}
        >
          {message.content}
        </ReactMarkdown>
      )}
    </div>
  );
}
```

---

## 4. 离线与弱网处理

| 场景 | 策略 |
|------|------|
| **弱网** | 请求超时 15s → 自动重试 1 次 → 展示重试按钮 |
| **离线** | 检测 `navigator.onLine`，顶部提示"网络不可用" |
| **学习记录** | 离线时暂存 IndexedDB，恢复后批量上报 |
| **游戏资源** | Service Worker 缓存游戏引擎 + 常用素材 |

---

*最后更新：2026-03-25*