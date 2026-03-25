# 管理后台 — 页面设计

> 父文档：[README.md](README.md) | API 参考：[admin](../api/admin.md)、[content-engine](../api/content-engine.md)  
> 技术栈：React 18 + TypeScript + Vite 5 + Ant Design 5 + ProComponents

---

## 1. 产品定位

管理后台供**运营管理员 (admin)** 使用，核心场景：

- 教材上传与解析管理
- AI 生成内容审核与发布
- 学习任务编排与发布
- 用户管理（学生、家长、管理员）
- 数据统计与报表
- 系统配置（LLM 模型、通知模板等）

---

## 2. 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 管理员账号密码登录 |
| `/` | 仪表盘 | 核心指标 + 待办 |
| `/textbooks` | 教材管理 | 列表 + 上传 + 解析状态 |
| `/textbooks/:id` | 教材详情 | 章节树 + 知识点 |
| `/resources` | 资源管理 | AI 生成的互动内容 |
| `/resources/:id/review` | 内容审核 | 预览 + 通过/驳回 |
| `/tasks` | 任务管理 | 学习任务列表 |
| `/tasks/create` | 创建任务 | 任务编排表单 |
| `/tasks/:id` | 任务详情 | 资源列表 + 分配情况 |
| `/users` | 用户管理 | 用户列表 + 搜索 |
| `/users/:id` | 用户详情 | 学习档案 + 操作日志 |
| `/analytics` | 数据统计 | 图表仪表盘 |
| `/notifications` | 通知管理 | 模板 + 发送记录 |
| `/settings` | 系统设置 | LLM 配置等 |
| `/settings/models` | 模型管理 | Provider / 模型 / 路由 |

---

## 3. 布局结构

采用 `ProLayout` 标准后台布局：左侧菜单 + 顶部栏 + 内容区。

```
┌──────────────────────────────────────────────────┐
│ 🎓 知趣课堂 · 管理后台          🔔  admin ▼      │
├────────┬─────────────────────────────────────────┤
│ 📊 仪表盘│                                        │
│ 📚 教材  │         页面内容区域                     │
│ 🎮 内容  │    ProTable / ProForm / 图表            │
│ 📋 任务  │                                        │
│ 👥 用户  │                                        │
│ 📈 统计  │  面包屑：首页 / 教材管理 / 详情          │
│ ⚙️ 设置  │                                        │
├────────┴─────────────────────────────────────────┤
│ © 2026 知趣课堂                    v1.0.0        │
└──────────────────────────────────────────────────┘
```

```typescript
// layouts/AdminLayout.tsx
import { ProLayout } from '@ant-design/pro-components';

function AdminLayout() {
  return (
    <ProLayout
      title="知趣课堂"
      logo="/logo.svg"
      menuDataRender={() => menuConfig}
      rightContentRender={() => <HeaderRight />}
    >
      <Outlet />
    </ProLayout>
  );
}
```

---

## 4. 核心页面设计

### 4.1 仪表盘 `/`

```
┌──────────┬──────────┬──────────┬──────────┐
│ 活跃学生  │ 今日任务  │ 待审核    │ 教材总数  │
│   1,234  │   156    │   23     │   45     │
│  ↑12%    │  ↑8%     │  ↓5      │  +2     │
└──────────┴──────────┴──────────┴──────────┘

┌───────────────────────┐  ┌────────────────────┐
│ 📈 学习趋势 (7天)      │  │ 🔔 待办事项         │
│  (折线图: 学习时长     │  │ · 23个内容待审核    │
│   / 完成任务数)        │  │ · 5个教材解析中     │
│                       │  │ · 2个任务即将到期   │
└───────────────────────┘  └────────────────────┘
```

**图表库：** `@ant-design/charts`（基于 G2Plot）

**调用接口：**
- `GET /api/v1/admin/dashboard/stats` — 概览指标
- `GET /api/v1/admin/dashboard/trends?days=7` — 学习趋势
- `GET /api/v1/admin/dashboard/todos` — 待办事项

### 4.2 教材管理 `/textbooks`

使用 `ProTable` 实现带筛选、排序、分页的列表：

```typescript
const columns: ProColumns<Textbook>[] = [
  { title: '教材名称', dataIndex: 'title', ellipsis: true },
  {
    title: '学科', dataIndex: 'subject',
    valueEnum: subjectEnum,
    filters: true,
  },
  {
    title: '年级范围', dataIndex: 'grade_range',
    render: (_, r) => `${gradeLabel(r.grade_from)} ~ ${gradeLabel(r.grade_to)}`,
  },
  {
    title: '解析状态', dataIndex: 'parse_status',
    valueEnum: {
      pending:   { text: '待解析', status: 'Default' },
      parsing:   { text: '解析中', status: 'Processing' },
      completed: { text: '已完成', status: 'Success' },
      failed:    { text: '失败',   status: 'Error' },
    },
  },
  { title: '上传时间', dataIndex: 'created_at', valueType: 'dateTime', sorter: true },
  {
    title: '操作',
    render: (_, record) => (
      <Space>
        <Link to={`/textbooks/${record.id}`}>查看</Link>
        {record.parse_status === 'failed' && (
          <Button size="small" onClick={() => retryParse(record.id)}>重试</Button>
        )}
      </Space>
    ),
  },
];
```

**上传教材弹窗：** 文件类型 `.pdf / .docx / .pptx`，单文件最大 50MB，上传到 MinIO 后自动触发解析。

**调用接口：**
- `GET /api/v1/textbooks?page=1&size=20&subject=math`
- `POST /api/v1/textbooks`（multipart 上传）
- `POST /api/v1/textbooks/:id/retry-parse`

### 4.3 教材详情 `/textbooks/:id`

左侧章节树 + 右侧知识点列表：

```
┌──────────────┬────────────────────────────────┐
│ 📖 章节目录   │ 知识点列表                      │
│              │                                │
│ ▼ 第一章     │ ┌────────────────────────────┐  │
│   1.1 分数…  │ │ 分数的定义                  │  │
│ ► 1.2 分数…  │ │ 难度: ★★☆  标签: 概念       │  │
│   1.3 分数…  │ │ 关联资源: 3个               │  │
│ ▼ 第二章     │ ├────────────────────────────┤  │
│   2.1 小数…  │ │ 真分数与假分数              │  │
│              │ │ 难度: ★★★  标签: 分类       │  │
│              │ │ 关联资源: 2个               │  │
│              │ └────────────────────────────┘  │
└──────────────┴────────────────────────────────┘
```

**调用接口：**
- `GET /api/v1/textbooks/:id`
- `GET /api/v1/textbooks/:id/chapters`
- `GET /api/v1/chapters/:id/knowledge-points`

### 4.4 内容审核 `/resources/:id/review`

```
┌──────────────────────────┬─────────────────────────┐
│                          │ 📋 审核信息               │
│   [内容预览区域]          │                         │
│                          │ 类型: interactive_game   │
│   · 游戏: iframe 预览    │ 知识点: 分数的认识        │
│   · 视频: 播放器预览      │ 生成模型: DeepSeek-V3    │
│   · 练习: 题目渲染        │ 生成时间: 2026-03-25     │
│   · 思维导图: SVG 预览    │                         │
│                          │ [✅ 通过]  [❌ 驳回]     │
│                          │                         │
│                          │ 驳回理由：               │
│                          │ ┌─────────────────────┐ │
│                          │ │                     │ │
│                          │ └─────────────────────┘ │
└──────────────────────────┴─────────────────────────┘
```

**预览策略：**

| 资源类型 | 预览方式 |
|---------|---------|
| `interactive_game` | iframe 嵌入 Phaser 游戏 |
| `explainer_video` | 视频播放器 |
| `exercise_set` | 题目卡片渲染（选择/填空/判断） |
| `mind_map` | SVG / Mermaid 渲染 |

**调用接口：**
- `GET /api/v1/resources/:id` — 资源详情
- `POST /api/v1/resources/:id/review` — `{ action: 'approve' | 'reject', reason? }`

### 4.5 任务创建 `/tasks/create`

使用 `StepsForm` 分步创建：

| 步骤 | 内容 | 说明 |
|------|------|------|
| 1. 基本信息 | 名称、描述、学科、年级、截止日期 | `ProFormText` + `ProFormSelect` |
| 2. 资源编排 | 从已审核资源中选取，拖拽排序 | `ProTable` + `@dnd-kit/sortable` |
| 3. 分配目标 | 按年级批量 / 选择具体学生 | `Transfer` 穿梭框 |
| 4. 确认发布 | 预览 → 立即发布 / 定时发布 | `Descriptions` + `DatePicker` |

```typescript
<StepsForm onFinish={async (values) => {
  const taskId = await createTask(values);
  if (values.publishNow) {
    await publishTask(taskId);
  }
  message.success('任务创建成功');
}}>
  <StepsForm.StepForm title="基本信息">
    <ProFormText name="title" label="任务名称" rules={[{ required: true }]} />
    <ProFormSelect name="subject" label="学科" valueEnum={subjectEnum} />
    <ProFormDatePicker name="deadline" label="截止日期" />
  </StepsForm.StepForm>
  <StepsForm.StepForm title="资源编排">
    <ResourceSelector />
  </StepsForm.StepForm>
  {/* ... */}
</StepsForm>
```

**调用接口：**
- `GET /api/v1/resources?status=approved&subject=math`
- `POST /api/v1/tasks`
- `POST /api/v1/tasks/:id/publish`

### 4.6 用户管理 `/users`

```typescript
const columns: ProColumns<User>[] = [
  { title: '用户名', dataIndex: 'nickname', copyable: true },
  { title: '手机号', dataIndex: 'phone', render: maskPhone },
  {
    title: '角色', dataIndex: 'role',
    valueEnum: {
      student: { text: '学生', color: 'blue' },
      parent:  { text: '家长', color: 'green' },
      admin:   { text: '管理员', color: 'red' },
    },
    filters: true,
  },
  { title: '注册时间', dataIndex: 'created_at', valueType: 'dateTime', sorter: true },
  {
    title: '操作',
    render: (_, record) => (
      <Space>
        <Link to={`/users/${record.id}`}>详情</Link>
        <Popconfirm title="确认禁用？">
          <Button size="small" danger>禁用</Button>
        </Popconfirm>
      </Space>
    ),
  },
];
```

**手机号脱敏：** `138****1234` 格式展示，点击"查看"需二次鉴权。

**调用接口：**
- `GET /api/v1/admin/users?role=student&page=1&size=20`
- `GET /api/v1/admin/users/:id`
- `PATCH /api/v1/admin/users/:id` — 禁用/启用

### 4.7 数据统计 `/analytics`

| 图表 | 类型 | 数据源 |
|------|------|--------|
| 每日活跃用户 | 折线图 | `/admin/analytics/dau` |
| 学科任务完成率 | 柱状图 | `/admin/analytics/completion-by-subject` |
| 知识点难度分布 | 饼图 | `/admin/analytics/difficulty-distribution` |
| AI 对话量趋势 | 面积图 | `/admin/analytics/tutor-usage` |
| LLM 调用成本 | 堆叠柱状图 | `/admin/analytics/llm-cost` |

支持日期范围筛选（最近 7/30/90 天）和导出 CSV。

### 4.8 模型管理 `/settings/models`

管理 LLM Provider 和模型配置（对应 `model_providers`、`model_configs`、`model_routing_rules` 表）：

```
┌─────────────────────────────────────────────┐
│ 模型管理                          [+ 新增]   │
├─────────────────────────────────────────────┤
│ Provider   │ 模型名             │ 状态      │
│ DeepSeek   │ deepseek-v3       │ 🟢 启用   │
│ Qwen       │ qwen-2.5-72b     │ 🟢 启用   │
│ OpenAI     │ gpt-4o            │ 🟡 备用   │
│ Anthropic  │ claude-3.5-sonnet │ ⚪ 禁用   │
├─────────────────────────────────────────────┤
│ 路由规则                                     │
│ task_type=chat       → primary: deepseek-v3 │
│ task_type=embedding  → primary: qwen-embed  │
│ task_type=review     → primary: gpt-4o      │
└─────────────────────────────────────────────┘
```

---

## 5. 通用模式

### 5.1 权限控制

```typescript
// hooks/useAuth.ts
function useAuth() {
  const { user } = useStore();
  if (user?.role !== 'admin') {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
```

所有管理后台路由包裹在 `RequireAdmin` 守卫中。

### 5.2 请求层

复用 README 中定义的 `apiClient`（axios 封装），拦截器自动处理：
- 401 → 刷新 token 或跳转登录
- 403 → 提示无权限
- 统一错误 `message.error(res.message)`

### 5.3 列表页标准模式

所有列表页统一使用 `ProTable`：
- 顶部搜索栏（筛选 + 重置）
- 工具栏（新建按钮 + 刷新 + 密度切换）
- 分页（默认 20 条/页）
- 支持 URL 参数同步（`syncToUrl: true`）

---

## 6. 目录结构

```
admin/
├── src/
│   ├── api/                # 请求层
│   │   ├── client.ts       #   axios 实例
│   │   ├── textbook.ts     #   教材相关
│   │   ├── resource.ts     #   资源相关
│   │   ├── task.ts         #   任务相关
│   │   ├── user.ts         #   用户相关
│   │   └── analytics.ts    #   统计相关
│   ├── components/         # 共享组件
│   │   ├── ChapterTree/    #   章节树组件
│   │   ├── ResourcePreview/#   资源预览
│   │   └── StatCard/       #   统计卡片
│   ├── hooks/              # 自定义 Hook
│   ├── layouts/            # 布局组件
│   │   └── AdminLayout.tsx
│   ├── pages/              # 页面目录
│   │   ├── dashboard/
│   │   ├── textbooks/
│   │   ├── resources/
│   │   ├── tasks/
│   │   ├── users/
│   │   ├── analytics/
│   │   ├── notifications/
│   │   ├── settings/
│   │   └── login/
│   ├── stores/             # Zustand store
│   ├── utils/
│   ├── router.tsx          # React Router 配置
│   └── main.tsx            # 入口
├── index.html
├── vite.config.ts
└── package.json
```

---

*最后更新：2026-03-25*
