# 共享包开发规范 (packages/shared)

> 适用于 `packages/shared/` — 前端项目间共享的 TypeScript 代码  
> 消费方：`admin/`（管理后台）、`app/`（学生端 H5）、`miniapp/`（家长端小程序）  
> 最后更新：2026-03-26

---

## 目录

1. [项目结构](#1-项目结构)
2. [包管理与发布](#2-包管理与发布)
3. [类型定义规范](#3-类型定义规范)
4. [工具函数规范](#4-工具函数规范)
5. [常量与枚举](#5-常量与枚举)
6. [兼容性约束](#6-兼容性约束)
7. [测试规范](#7-测试规范)
8. [变更管理](#8-变更管理)

---

## 1. 项目结构

```
packages/shared/
├── src/
│   ├── types/                 # 共享类型定义
│   │   ├── api.ts             #   统一响应 / 分页 / 错误
│   │   ├── user.ts            #   用户、学生、家长
│   │   ├── content.ts         #   教材、章节、知识点
│   │   ├── media.ts           #   互动资源
│   │   ├── learning.ts        #   学习任务、进度
│   │   ├── analytics.ts       #   统计、报告
│   │   ├── tutor.ts           #   AI 辅导对话
│   │   └── notification.ts    #   通知
│   ├── constants/             # 共享常量
│   │   ├── enums.ts           #   枚举值（与后端对齐）
│   │   ├── roles.ts           #   角色定义
│   │   └── errors.ts          #   错误码
│   ├── utils/                 # 纯函数工具
│   │   ├── format.ts          #   日期 / 数字格式化
│   │   ├── validate.ts        #   手机号 / 验证码校验
│   │   ├── grade.ts           #   年级/学科映射
│   │   └── id.ts              #   UUID 相关
│   └── index.ts               # 统一导出
├── __tests__/                 # 测试
├── package.json
├── tsconfig.json
├── DEV-GUIDE.md               # 本文件
└── README.md
```

---

## 2. 包管理与发布

### 2.1 Monorepo 内部包

采用 workspace 协议（pnpm / yarn）引用，无需发布到 npm：

```json
// admin/package.json
{
  "dependencies": {
    "@zhiqu/shared": "workspace:*"
  }
}
```

### 2.2 构建

使用 `tsup` 或 `tsc` 编译，输出 ESM + CJS：

```json
// package.json
{
  "name": "@zhiqu/shared",
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsup src/index.ts --format esm,cjs --dts",
    "dev": "tsup src/index.ts --format esm,cjs --dts --watch"
  }
}
```

### 2.3 导出管理

通过 `src/index.ts` 统一管理公共 API：

```typescript
// src/index.ts
// Types
export type { ApiResponse, PaginatedResponse, ApiError } from './types/api';
export type { UserInfo, StudentProfile, GuardianBinding } from './types/user';
export type { Textbook, Chapter, KnowledgePoint } from './types/content';
// ...

// Constants
export { SUBJECTS, GRADES, ROLES, ERROR_CODES } from './constants/enums';

// Utils
export { formatDate, formatDuration, formatNumber } from './utils/format';
export { isValidPhone, isValidCode } from './utils/validate';
export { gradeLabel, subjectLabel } from './utils/grade';
```

> **原则**：只导出消费方确实需要的内容。未导出的模块视为内部实现。

---

## 3. 类型定义规范

### 3.1 API 响应类型

与后端统一响应格式对齐：

```typescript
// types/api.ts

/** 标准响应 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
}

/** 分页响应 */
export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** 分页响应快捷类型 */
export type PaginatedResponse<T> = ApiResponse<PaginatedData<T>>;

/** API 错误 */
export interface ApiError {
  code: number;
  message: string;
  details?: Record<string, string[]>;
  request_id?: string;
}
```

### 3.2 业务实体类型

字段命名与后端 API 返回字段**完全一致**（snake_case）：

```typescript
// types/user.ts
export interface UserInfo {
  id: string;
  phone: string;
  role: UserRole;
  nickname: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface StudentProfile {
  id: string;
  user_id: string;
  school: string | null;
  grade: Grade;
  learning_preference: LearningPreference | null;
}
```

### 3.3 类型守则

| 规则 | 说明 |
|------|------|
| 不使用 `any` | 用 `unknown` 替代 |
| 不使用 `enum` | 用联合类型 + const 对象 |
| 可选字段用 `\| null` | 与 API 返回对齐 |
| 日期用 `string` | ISO 8601 字符串 |
| ID 用 `string` | UUID |
| 命名：接口用 PascalCase | `UserInfo`, `Textbook` |
| 命名：类型别名同上 | `type Grade = 'grade_1' \| ...` |

---

## 4. 工具函数规范

### 4.1 纯函数

所有工具函数必须是**纯函数**（无副作用，无 IO，无 DOM/平台 API）：

```typescript
// ✅ 纯函数
export const formatDate = (iso: string, pattern?: string): string => { ... };
export const isValidPhone = (phone: string): boolean => /^1[3-9]\d{9}$/.test(phone);

// ❌ 不纯（依赖平台 API）
export const getScreenWidth = () => window.innerWidth; // 禁止
export const readStorage = (key: string) => localStorage.getItem(key); // 禁止
```

> 平台相关工具放到各子项目自己的 `utils/` 中。

### 4.2 格式化工具

```typescript
// utils/format.ts
import { GRADE_LABELS, SUBJECT_LABELS } from '../constants/enums';

/** 日期格式化（轻量，不引入 dayjs） */
export const formatDate = (iso: string, pattern = 'YYYY-MM-DD'): string => {
  const d = new Date(iso);
  const map: Record<string, string> = {
    YYYY: String(d.getFullYear()),
    MM: String(d.getMonth() + 1).padStart(2, '0'),
    DD: String(d.getDate()).padStart(2, '0'),
    HH: String(d.getHours()).padStart(2, '0'),
    mm: String(d.getMinutes()).padStart(2, '0'),
  };
  return pattern.replace(/YYYY|MM|DD|HH|mm/g, (m) => map[m]);
};

/** 学习时长格式化：秒 → "Xh Ym" / "Ym" */
export const formatDuration = (seconds: number): string => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
};

/** 数字千分位 */
export const formatNumber = (n: number): string =>
  n.toLocaleString('zh-CN');
```

### 4.3 校验工具

```typescript
// utils/validate.ts

/** 手机号校验（中国大陆） */
export const isValidPhone = (phone: string): boolean =>
  /^1[3-9]\d{9}$/.test(phone);

/** 验证码校验（6位数字） */
export const isValidCode = (code: string): boolean =>
  /^\d{6}$/.test(code);
```

---

## 5. 常量与枚举

### 5.1 枚举定义

使用 `as const` + 联合类型：

```typescript
// constants/enums.ts

/** 用户角色 */
export const ROLES = ['student', 'guardian', 'admin', 'teacher'] as const;
export type UserRole = (typeof ROLES)[number];

/** 学科 */
export const SUBJECTS = [
  'math', 'chinese', 'english', 'physics',
  'chemistry', 'biology', 'history', 'geography', 'politics',
] as const;
export type Subject = (typeof SUBJECTS)[number];

/** 年级 */
export const GRADES = [
  'grade_1', 'grade_2', 'grade_3', 'grade_4', 'grade_5', 'grade_6',
  'grade_7', 'grade_8', 'grade_9', 'grade_10', 'grade_11', 'grade_12',
] as const;
export type Grade = (typeof GRADES)[number];

/** 解析状态 */
export const PARSE_STATUSES = ['pending', 'parsing', 'completed', 'failed'] as const;
export type ParseStatus = (typeof PARSE_STATUSES)[number];

/** 任务状态 */
export const TASK_STATUSES = ['draft', 'active', 'expired', 'archived'] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];
```

### 5.2 中文标签映射

```typescript
// constants/enums.ts (续)

export const SUBJECT_LABELS: Record<Subject, string> = {
  math: '数学', chinese: '语文', english: '英语',
  physics: '物理', chemistry: '化学', biology: '生物',
  history: '历史', geography: '地理', politics: '政治',
};

export const GRADE_LABELS: Record<Grade, string> = {
  grade_1: '一年级', grade_2: '二年级', grade_3: '三年级',
  grade_4: '四年级', grade_5: '五年级', grade_6: '六年级',
  grade_7: '初一', grade_8: '初二', grade_9: '初三',
  grade_10: '高一', grade_11: '高二', grade_12: '高三',
};
```

### 5.3 错误码

```typescript
// constants/errors.ts

export const ERROR_CODES = {
  // 通用
  SUCCESS: 0,
  UNKNOWN: -1,
  VALIDATION_ERROR: 1001,
  UNAUTHORIZED: 1002,
  FORBIDDEN: 1003,
  NOT_FOUND: 1004,
  RATE_LIMITED: 1005,

  // 认证
  INVALID_CODE: 2001,
  CODE_EXPIRED: 2002,
  PHONE_NOT_BOUND: 2003,
  TOKEN_EXPIRED: 2004,

  // 业务
  TEXTBOOK_PARSE_FAILED: 3001,
  GENERATION_FAILED: 3002,
  TASK_NOT_AVAILABLE: 3003,
} as const;
```

---

## 6. 兼容性约束

`@zhiqu/shared` 被三个不同运行环境消费，必须遵守：

| 约束 | 原因 |
|------|------|
| **不引入 DOM API** | 小程序无 `window`/`document` |
| **不引入 Node API** | 浏览器无 `fs`/`path` |
| **不引入运行时依赖** | 保持零依赖，减少消费方体积 |
| **ES2020 target** | 兼容小程序 JS 引擎 |
| **不使用 `globalThis`** | 部分小程序引擎不支持 |

> 如需平台特定功能（如 `dayjs`、`axios`），在消费方项目中引入。

---

## 7. 测试规范

### 7.1 测试工具

| 工具 | 用途 |
|------|------|
| Vitest / Jest | 运行器 |
| TypeScript | 类型校验即测试 |

### 7.2 测试文件

```
packages/shared/
  __tests__/
    format.test.ts
    validate.test.ts
    grade.test.ts
```

### 7.3 测试示例

```typescript
// __tests__/validate.test.ts
import { isValidPhone, isValidCode } from '../src/utils/validate';

describe('isValidPhone', () => {
  it('accepts valid phone numbers', () => {
    expect(isValidPhone('13800138000')).toBe(true);
    expect(isValidPhone('19912345678')).toBe(true);
  });

  it('rejects invalid phone numbers', () => {
    expect(isValidPhone('12345')).toBe(false);
    expect(isValidPhone('2381234567')).toBe(false);
    expect(isValidPhone('')).toBe(false);
  });
});

describe('isValidCode', () => {
  it('accepts 6-digit codes', () => {
    expect(isValidCode('123456')).toBe(true);
  });
  it('rejects non-6-digit', () => {
    expect(isValidCode('12345')).toBe(false);
    expect(isValidCode('abcdef')).toBe(false);
  });
});
```

### 7.4 覆盖率目标

| 类别 | 覆盖率 |
|------|--------|
| 工具函数 | ≥ 90% |
| 常量/类型 | TypeScript 编译即可 |

---