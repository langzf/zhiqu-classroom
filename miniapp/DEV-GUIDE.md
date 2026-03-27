# 家长端微信小程序开发规范 (miniapp)

> 适用于 `miniapp/` 家长端微信小程序  
> 技术栈：Taro 3 · React · TypeScript 5 · NutUI · Zustand  
> 最后更新：2026-03-26

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
9. [小程序专项规范](#9-小程序专项规范)
10. [Git 与协作](#10-git-与协作)

---

## 1. 项目结构

```
miniapp/
├── src/
│   ├── api/                   # API 请求层
│   │   ├── client.ts          #   Taro.request 封装
│   │   ├── auth.ts            #   认证/微信登录 API
│   │   ├── user.ts            #   用户/绑定 API
│   │   ├── analytics.ts       #   统计/报告 API
│   │   └── notification.ts    #   通知 API
│   ├── components/            # 通用 UI 组件
│   │   ├── ChildCard/         #   孩子卡片
│   │   ├── StatBlock/         #   数据块
│   │   ├── NotifyItem/        #   通知项
│   │   ├── Empty/             #   空状态
│   │   └── Loading/           #   加载占位
│   ├── hooks/                 # 自定义 Hooks
│   │   ├── useAuth.ts
│   │   ├── useChildren.ts
│   │   └── useNotification.ts
│   ├── pages/                 # 页面目录
│   │   ├── index/             #   首页（孩子列表 + 概览）
│   │   ├── login/             #   微信授权 + 手机号绑定
│   │   ├── child/             #   孩子学习详情
│   │   ├── report/            #   报告列表/详情
│   │   ├── notifications/     #   通知中心
│   │   ├── profile/           #   个人中心/设置
│   │   └── bind/              #   绑定孩子
│   ├── stores/                # Zustand stores
│   │   ├── authStore.ts
│   │   ├── childrenStore.ts
│   │   └── notificationStore.ts
│   ├── types/                 # 类型定义
│   │   ├── api.ts             #   接口类型
│   │   ├── user.ts            #   用户/孩子类型
│   │   └── report.ts          #   报告类型
│   ├── utils/                 # 工具函数
│   │   ├── storage.ts         #   Taro.getStorage 封装
│   │   ├── format.ts          #   日期/数字格式化
│   │   └── logger.ts          #   日志上报
│   ├── constants/             # 常量
│   │   ├── api.ts             #   BASE_URL、接口路径
│   │   └── enums.ts           #   枚举值
│   ├── app.config.ts          # 小程序全局配置
│   ├── app.ts                 # 入口文件
│   └── app.scss               # 全局样式
├── config/                    # Taro 构建配置
│   ├── index.ts
│   ├── dev.ts
│   └── prod.ts
├── project.config.json        # 微信开发者工具配置
├── project.private.config.json
├── package.json
├── tsconfig.json
├── babel.config.js
├── DEV-GUIDE.md               # 本文件
└── README.md
```

### 1.1 命名约定

| 类型 | 规范 | 示例 |
|------|------|------|
| 页面目录 | kebab-case | `pages/child/detail.tsx` |
| 组件文件 | PascalCase | `ChildCard.tsx`, `StatBlock.tsx` |
| 组件目录 | PascalCase | `components/ChildCard/index.tsx` |
| Hooks | camelCase，use 前缀 | `useChildren.ts` |
| Store | camelCase，Store 后缀 | `authStore.ts` |
| 工具函数 | camelCase | `format.ts` |
| 类型文件 | camelCase | `api.ts` |
| 样式文件 | 与组件同名 | `ChildCard.module.scss` |
| 常量 | UPPER_SNAKE_CASE | `MAX_CHILDREN = 5` |

### 1.2 导入顺序

```typescript
// 1. React / Taro
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';

// 2. 第三方库
import { Cell, Tag } from '@nutui/nutui-react-taro';

// 3. 内部模块（stores → hooks → api → utils → types）
import { useChildrenStore } from '@/stores/childrenStore';
import { useAuth } from '@/hooks/useAuth';
import { analyticsApi } from '@/api/analytics';
import { formatDate } from '@/utils/format';
import type { ChildInfo } from '@/types/user';

// 4. 组件
import { ChildCard } from '@/components/ChildCard';

// 5. 样式
import './index.scss';
```

---

## 2. TypeScript 编码规范

### 2.1 严格模式

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "exactOptionalPropertyTypes": false,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### 2.2 类型定义

```typescript
// ✅ 接口响应类型
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
}

// ✅ 业务实体类型
interface ChildInfo {
  student_id: string;
  name: string;
  avatar_url: string | null;
  grade: string;
  school: string;
}

// ✅ 页面参数类型
interface ChildDetailParams {
  studentId: string;
}

// ❌ 禁止 any
const data: any = res.data; // 不允许
```

### 2.3 枚举处理

使用 `const enum` 或联合类型，避免运行时枚举：

```typescript
// ✅ 联合类型（推荐）
type NotificationType = 'task_complete' | 'report_ready' | 'task_remind';

// ✅ const 对象（需要值映射时）
const NOTIFICATION_LABEL = {
  task_complete: '任务完成',
  report_ready: '报告生成',
  task_remind: '任务提醒',
} as const;

// ❌ 运行时 enum
enum NotificationType { ... } // 避免
```

---

## 3. React 组件规范

### 3.1 函数组件

所有组件使用函数式 + Hooks，不使用 Class 组件：

```typescript
// ✅ 标准组件写法
interface ChildCardProps {
  child: ChildInfo;
  stats?: TodayStats;
  onTap?: () => void;
}

const ChildCard: React.FC<ChildCardProps> = ({ child, stats, onTap }) => {
  return (
    <View className="child-card" onClick={onTap}>
      <Image className="child-card__avatar" src={child.avatar_url || DEFAULT_AVATAR} />
      <View className="child-card__info">
        <Text className="child-card__name">{child.name}</Text>
        <Text className="child-card__grade">{child.grade}</Text>
      </View>
      {stats && (
        <View className="child-card__stats">
          <StatBlock label="学习时长" value={`${stats.duration}min`} />
          <StatBlock label="完成率" value={`${stats.completion}%`} />
        </View>
      )}
    </View>
  );
};

export default ChildCard;
```

### 3.2 组件分类

| 分类 | 目录 | 特征 |
|------|------|------|
| 页面组件 | `pages/` | 对应路由，可调用 API |
| 业务组件 | `components/` | 含业务逻辑，可引用 store |
| 基础组件 | NutUI 直接使用 | 不封装无意义的包装层 |

### 3.3 Taro 组件使用

使用 `@tarojs/components` 替代 HTML 标签：

```typescript
// ✅ Taro 组件
import { View, Text, Image, ScrollView } from '@tarojs/components';

// ❌ HTML 标签（小程序不支持）
<div>, <span>, <img> // 禁止
```

---

## 4. 状态管理

使用 Zustand，与 app/ 和 admin/ 保持一致。

### 4.1 Store 模板

```typescript
// stores/childrenStore.ts
import { create } from 'zustand';
import { userApi } from '@/api/user';
import type { ChildInfo } from '@/types/user';

interface ChildrenState {
  children: ChildInfo[];
  loading: boolean;
  error: string | null;
  fetchChildren: () => Promise<void>;
  clearChildren: () => void;
}

export const useChildrenStore = create<ChildrenState>((set) => ({
  children: [],
  loading: false,
  error: null,

  fetchChildren: async () => {
    set({ loading: true, error: null });
    try {
      const res = await userApi.getGuardianBindings();
      set({ children: res.data.items, loading: false });
    } catch (err) {
      set({ error: '加载失败', loading: false });
    }
  },

  clearChildren: () => set({ children: [], error: null }),
}));
```

### 4.2 持久化

小程序环境使用 `Taro.getStorageSync` / `setStorageSync`：

```typescript
// utils/storage.ts
export const storage = {
  get: <T>(key: string): T | null => {
    try {
      const val = Taro.getStorageSync(key);
      return val ? JSON.parse(val) : null;
    } catch {
      return null;
    }
  },
  set: (key: string, value: unknown) => {
    Taro.setStorageSync(key, JSON.stringify(value));
  },
  remove: (key: string) => {
    Taro.removeStorageSync(key);
  },
};
```

Token 持久化：

```typescript
// stores/authStore.ts — 登录后写入 storage
login: async (code: string) => {
  const res = await authApi.wxLogin({ code, role: 'parent' });
  storage.set('access_token', res.data.access_token);
  storage.set('refresh_token', res.data.refresh_token);
  set({ token: res.data.access_token, user: res.data.user });
},
```

---

## 5. API 请求层

### 5.1 请求封装

小程序环境不支持 XMLHttpRequest，使用 `Taro.request` 封装：

```typescript
// api/client.ts
import Taro from '@tarojs/taro';
import { storage } from '@/utils/storage';
import { BASE_URL } from '@/constants/api';

interface RequestOptions {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  data?: Record<string, unknown>;
  header?: Record<string, string>;
}

export const request = async <T>(options: RequestOptions): Promise<ApiResponse<T>> => {
  const token = storage.get<string>('access_token');

  const res = await Taro.request({
    url: `${BASE_URL}${options.url}`,
    method: options.method || 'GET',
    data: options.data,
    header: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.header,
    },
  });

  // 401 → 尝试刷新 token
  if (res.statusCode === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return request(options); // 重试
    }
    Taro.redirectTo({ url: '/pages/login/index' });
    throw new Error('Unauthorized');
  }

  if (res.statusCode >= 400) {
    throw new Error(res.data?.message || `HTTP ${res.statusCode}`);
  }

  return res.data as ApiResponse<T>;
};
```

### 5.2 API 模块化

```typescript
// api/analytics.ts
import { request } from './client';
import type { TodayStats, WeeklyReport } from '@/types/report';

export const analyticsApi = {
  getTodayStats: (studentId: string) =>
    request<TodayStats>({ url: `/api/v1/analytics/study-stats/${studentId}/today` }),

  getWeeklyReport: (studentId: string, weekStart: string) =>
    request<WeeklyReport>({
      url: `/api/v1/analytics/reports`,
      data: { student_id: studentId, type: 'weekly', week_start: weekStart },
    }),
};
```

### 5.3 错误处理

```typescript
// 统一错误提示
const showError = (msg: string) => {
  Taro.showToast({ title: msg, icon: 'none', duration: 2000 });
};

// 页面中使用
const loadData = async () => {
  try {
    await childrenStore.fetchChildren();
  } catch