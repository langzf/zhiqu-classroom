# 家长端微信小程序 — 页面设计

> 父文档：[README.md](README.md) | 技术栈：Taro 3 + React + TypeScript + NutUI

---

## 1. 产品定位

家长端为**只读监控 + 轻量操作**客户端，核心场景：

- 查看孩子学习进度与报告
- 接收系统通知（任务完成、周报生成）
- 管理亲子绑定关系
- 设置学习偏好

> 家长端不包含教材管理、内容审核等管理功能。

---

## 2. 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `pages/login/index` | 登录 | 微信授权 + 手机号绑定 |
| `pages/index/index` | 首页 | 孩子列表 + 今日概览 |
| `pages/child/detail` | 孩子详情 | 学习数据 + 最近任务 |
| `pages/report/list` | 报告列表 | 周报/月报 |
| `pages/report/detail` | 报告详情 | 图表 + 知识掌握度 |
| `pages/notifications/index` | 通知中心 | 系统消息列表 |
| `pages/profile/index` | 个人中心 | 设置 + 绑定管理 |
| `pages/bind/index` | 绑定孩子 | 输入绑定码 |

### Taro 路由配置

```typescript
// app.config.ts
export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/login/index',
    'pages/child/detail',
    'pages/report/list',
    'pages/report/detail',
    'pages/notifications/index',
    'pages/profile/index',
    'pages/bind/index',
  ],
  tabBar: {
    list: [
      { pagePath: 'pages/index/index', text: '首页', iconPath: '...', selectedIconPath: '...' },
      { pagePath: 'pages/notifications/index', text: '通知', iconPath: '...', selectedIconPath: '...' },
      { pagePath: 'pages/profile/index', text: '我的', iconPath: '...', selectedIconPath: '...' },
    ],
  },
  window: {
    navigationBarTitleText: '知趣课堂',
    navigationBarBackgroundColor: '#4F46E5',
    navigationBarTextStyle: 'white',
  },
});
```

---

## 3. 核心页面设计

### 3.1 登录页

**流程：**
1. 微信授权登录 → `wx.login()` 获取 code
2. 调用 `POST /api/v1/auth/wx/login` 换取 token
3. 如果是新用户 → 弹出手机号绑定弹窗
4. 绑定成功 → 跳转首页

```typescript
// 微信登录
const wxLogin = async () => {
  const { code } = await Taro.login();
  const res = await authApi.wxLogin({ code, role: 'parent' });
  if (res.data.need_bindPhone) {
    setShowPhoneBind(true);
  } else {
    setToken(res.data);
    Taro.switchTab({ url: '/pages/index/index' });
  }
};
```

### 3.2 首页

```
┌────────────────────────────┐
│ 知趣课堂 · 家长端           │
├────────────────────────────┤
│ 👦 小明（三年级）           │
│ ┌────────────────────────┐ │
│ │ 今日学习 45min          │ │
│ │ 完成任务 3/5            │ │
│ │ 本周正确率 85%          │ │
│ └────────────────────────┘ │
│                            │
│ 👧 小红（一年级）           │
│ ┌────────────────────────┐ │
│ │ 今日学习 30min          │ │
│ │ 完成任务 2/3            │ │
│ │ 本周正确率 90%          │ │
│ └────────────────────────┘ │
│                            │
│ [+ 绑定孩子]               │
├────────────────────────────┤
│  🏠 首页 │ 🔔 通知 │ 👤 我的│
└────────────────────────────┘
```

**数据加载：**
- `GET /api/v1/users/me/guardian-bindings` — 已绑定孩子列表
- `GET /api/v1/analytics/study-stats/:studentId/today` — 孩子今日数据

### 3.3 孩子详情页

```
┌────────────────────────────┐
│ ← 小明的学习                │
├────────────────────────────┤
│ [头像]  小明                │
│ 三年级 · 实验小学 · 数学     │
├────────────────────────────┤
│ 📊 本周概览                 │
│ 学习时长    完成率    正确率  │
│  4.5h       83%      82%   │
├────────────────────────────┤
│ 📋 最近任务                 │
│ ✅ 分数的认识  3/25 完成     │
│ 🔵 分数的比较  进行中        │
│ ○  小数初步    未开始        │
├────────────────────────────┤
│ ⚠️ 薄弱知识点               │
│ · 分数的比较 (掌握度 60%)   │
│ · 分数加减法 (掌握度 55%)   │
├────────────────────────────┤
│ [查看完整报告 →]            │
└────────────────────────────┘
```

**调用接口：**
- `GET /api/v1/analytics/study-stats/:studentId` — 学习统计
- `GET /api/v1/assignments?student_id=:id&limit=10` — 最近任务
- `GET /api/v1/analytics/knowledge-mastery/:studentId` — 知识掌握

### 3.4 报告详情

与学生端报告页类似，但为家长视角：
- 使用 `@antv/f2`（移动端图表库）渲染雷达图、折线图
- 显示本周 vs 上周对比
- 底部附"学习建议"（后端生成的文字摘要）

### 3.5 通知中心

```
┌────────────────────────────┐
│ 🔔 通知                     │
├────────────────────────────┤
│ 📋 小明完成了"分数的认识"   │
│    今天 14:30               │
│                            │
│ 📊 小明的周报已生成         │
│    3月24日 08:00            │
│                            │
│ ⚠️ 小红有3个任务即将到期    │
│    3月23日 20:00            │
└────────────────────────────┘
```

**调用接口：**
- `GET /api/v1/notifications/mine?page=1&size=20`
- `PATCH /api/v1/notifications/:id/read` — 标记已读

### 3.6 绑定孩子

流程：学生端生成绑定码 → 家长输入绑定码 → 建立监护关系

```
输入孩子的绑定码：
┌────────────────────────────┐
│  [  ] [  ] [  ] [  ] [  ]  │   6位数字
└────────────────────────────┘
          [确认绑定]
```

**调用接口：**
- `POST /api/v1/users/me/guardian-bindings` — `{ bind_code: "123456" }`

---

## 4. 小程序特有适配

### 4.1 分享

```typescript
// 每个页面配置分享
useShareAppMessage(() => ({
  title: '知趣课堂 - 让学习更有趣',
  path: '/pages/index/index',
  imageUrl: '/assets/share-cover.png',
}));
```

### 4.2 消息订阅

使用微信订阅消息推送通知：

```typescript
// 引导用户订阅
const requestSubscribe = () => {
  Taro.requestSubscribeMessage({
    tmplIds: [
      'TMPL_TASK_COMPLETE',   // 孩子完成任务
      'TMPL_REPORT_READY',    // 周报生成
      'TMPL_TASK_REMIND',     // 任务即将到期
    ],
  });
};
```

### 4.3 网络请求适配

Taro 环境使用 `Taro.request` 替代 axios：

```typescript
// api/client.ts (小程序版)
import Taro from '@tarojs/taro';

const request = async <T>(options: RequestOptions): Promise<ApiResponse<T>> => {
  const token = Taro.getStorageSync('access_token');
  const res = await Taro.request({
    url: `${BASE_URL}${options.url}`,
    method: options.method || 'GET',
    data: options.data,
    header: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
  });

  if (res.statusCode === 401) {
    const refreshed = await tryRefresh();
    if (!refreshed) {
      Taro.redirectTo({ url: '/pages/login/index' });
      throw new Error('Unauthorized');
    }
    return request(options); // 重试
  }

  return res.data as ApiResponse<T>;
};
```

---

## 5. 目录结构

```
miniapp/
├── src/
│   ├── api/              # 请求层
│   ├── components/       # 共享组件
│   │   ├── ChildCard/    #   孩子卡片
│   │   ├── StatBlock/    #   数据块
│   │   └── NotifyItem/   #   通知项
│   ├── hooks/            # 自定义 Hook
│   ├── pages/            # 页面目录
│   │   ├── index/
│   │   ├── login/
│   │   ├── child/
│   │   ├── report/
│   │   ├── notifications/
│   │   ├── profile/
│   │   └── bind/
│   ├── stores/           # Zustand store
│   ├── utils/
│   └── app.config.ts     # 小程序配置
├── project.config.json   # 微信开发者工具配置
└── package.json
```

---

*最后更新：2026-03-25*
