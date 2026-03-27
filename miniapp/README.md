# 家长端微信小程序 (miniapp)

> 基于 Taro 3 + React + TypeScript 的微信小程序

## 技术栈

| 维度 | 选型 |
|------|------|
| 框架 | Taro 3 + React |
| 语言 | TypeScript 5 |
| UI 库 | NutUI / Taro UI |
| 状态管理 | Zustand |
| 构建工具 | Taro CLI |
| 目标平台 | 微信小程序 |

## 目录结构

```
miniapp/
├── src/
│   ├── api/              # API 请求层
│   ├── components/       # 通用组件
│   ├── hooks/            # 自定义 Hook
│   ├── pages/            # 页面（按路由组织）
│   │   ├── index/        #   首页
│   │   ├── tasks/        #   学习任务
│   │   ├── reports/      #   学习报告
│   │   ├── profile/      #   个人中心
│   │   └── bind/         #   绑定学生
│   ├── stores/           # Zustand store
│   ├── utils/            # 工具函数
│   ├── types/            # TypeScript 类型
│   ├── styles/           # 全局样式
│   ├── constants/        # 常量/枚举
│   ├── app.ts            # 应用入口
│   └── app.config.ts     # Taro 配置
├── config/               # Taro 构建配置
├── project.config.json   # 微信小程序项目配置
├── package.json
├── tsconfig.json
├── DEV-GUIDE.md          # 开发规范
└── README.md
```

## 快速开始

```bash
# 安装依赖（项目根目录）
pnpm install

# 开发模式（需要微信开发者工具打开 miniapp/dist）
pnpm --filter miniapp dev

# 构建
pnpm --filter miniapp build
```

## 核心页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `/pages/index/index` | 已绑定学生的学习概览 |
| 任务列表 | `/pages/tasks/index` | 查看学生待完成 / 已完成任务 |
| 任务详情 | `/pages/tasks/detail` | 单个任务完成情况 |
| 学习报告 | `/pages/reports/index` | 周报 / 月报 |
| 绑定学生 | `/pages/bind/index` | 通过邀请码绑定 |
| 个人中心 | `/pages/profile/index` | 账户信息、退出登录 |

## 部署

通过微信开发者工具上传 → 提交审核 → 发布。

---

*最后更新：2026-03-25*
