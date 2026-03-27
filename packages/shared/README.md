# 共享包 @zhiqu/shared

> 三端前端项目（学生端、家长端、管理后台）共享的 TypeScript 类型、工具函数和常量

## 目录结构

```
packages/shared/
├── src/
│   ├── types/            # 共享 TypeScript 类型
│   │   ├── api.ts        #   API 响应类型
│   │   ├── user.ts       #   用户模型
│   │   ├── task.ts       #   任务模型
│   │   ├── content.ts    #   教材/知识点模型
│   │   └── enums.ts      #   枚举（学科、年级、角色等）
│   ├── utils/            # 共享工具函数
│   │   ├── format.ts     #   日期/时间格式化
│   │   ├── validate.ts   #   手机号等校验
│   │   └── token.ts      #   JWT 解析（不含存储逻辑）
│   ├── constants/        # 共享常量
│   │   ├── subjects.ts   #   学科列表
│   │   └── grades.ts     #   年级列表
│   └── index.ts          # 统一导出
├── package.json
├── tsconfig.json
├── DEV-GUIDE.md
└── README.md
```

## 使用方式

```typescript
// 在 app / admin / miniapp 中引用
import { Subject, Grade, UserRole, type ApiResponse } from '@zhiqu/shared';
import { formatDate, isValidPhone } from '@zhiqu/shared/utils';
```

## 开发

```bash
# 修改后会被 pnpm workspace 自动链接，无需手动构建
# 如需单独构建
pnpm --filter @zhiqu/shared build
```

## 发包规则

- 本包仅在 monorepo 内使用，不发布到 npm
- 通过 `workspace:*` 协议引用

---

*最后更新：2026-03-25*
