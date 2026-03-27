# 管理后台开发规范 (admin)

> 适用于 `admin/` 管理后台 Web 应用  
> 技术栈：React 18 · TypeScript 5 · Vite · Ant Design 5 · Zustand · React Router  
> 最后更新：2026-03-25

---

## 目录

1. [项目结构](#1-项目结构)
2. [编码规范](#2-编码规范)
3. [组件规范](#3-组件规范)
4. [路由与权限](#4-路由与权限)
5. [API 请求层](#5-api-请求层)
6. [样式规范](#6-样式规范)
7. [日志与错误处理](#7-日志与错误处理)
8. [表格与表单](#8-表格与表单)
9. [测试规范](#9-测试规范)
10. [Git 与协作](#10-git-与协作)

---

## 1. 项目结构

```
admin/
├── public/
├── src/
│   ├── api/                   # API 请求层
│   │   ├── client.ts          #   Axios 实例（与 app 共享配置模式）
│   │   ├── admin.ts           #   管理接口
│   │   ├── content.ts         #   教材管理
│   │   ├── analytics.ts       #   统计报表
│   │   └── user.ts            #   用户管理
│   ├── components/            # 通用组件
│   │   ├── layout/            #   ProLayout、侧边栏、面包屑
│   │   ├── table/             #   增强表格（筛选、导出）
│   │   └── business/          #   业务组件（TextbookUploader 等）
│   ├── hooks/
│   ├── pages/                 # 页面（按菜单模块组织）
│   │   ├── dashboard/         #   数据看板
│   │   ├── textbooks/         #   教材管理
│   │   ├── content/           #   内容管理
│   │   ├── tasks/             #   任务管理
│   │   ├── users/             #   用户管理
│   │   ├── analytics/         #   统计报表
│   │   ├── system/            #   系统配置
│   │   └── login/             #   登录
│   ├── stores/
│   ├── styles/
│   ├── types/
│   ├── utils/
│   ├── constants/
│   │   └── permissions.ts     #   权限常量
│   ├── router/
│   │   ├── index.tsx
│   │   └── authGuard.tsx      #   路由守卫
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
├── DEV-GUIDE.md               # 本文件
└── README.md
```

### 1.1 命名约定

与学生端一致（参考 `app/DEV-GUIDE.md` §1.1），额外约定：

| 类型 | 规范 | 示例 |
|------|------|------|
| 页面组件 | `{Resource}List` / `{Resource}Detail` | `TextbookList.tsx` |
| 表单组件 | `{Resource}Form` | `TextbookForm.tsx` |
| 弹窗组件 | `{Resource}Modal` | `TextbookUploadModal.tsx` |

---

## 2. 编码规范

与学生端共享 TypeScript 编码规范（参考 `app/DEV-GUIDE.md` §2），以下为管理后台特有约定：

### 2.1 Ant Design 按需导入

```typescript
// ✅ 按需导入
import { Button, Table, Form, Input, Select, message } from 'antd';

// ❌ 不要全量导入
import antd from 'antd';
```

### 2.2 ProComponents

优先使用 `@ant-design/pro-components` 提升开发效率：

```typescript
import { ProTable, ProForm, ProLayout } from '@ant-design/pro-components';
```

---

## 3. 组件规范

### 3.1 列表页模板

```tsx
export function TextbookList() {
  return (
    <ProTable<Textbook>
      headerTitle="教材管理"
      rowKey="id"
      request={async (params) => {
        const res = await adminApi.listTextbooks(params);
        return { data: res.data.items, total: res.data.total, success: true };
      }}
      columns={columns}
      toolBarRender={() => [
        <Button key="upload" type="primary" onClick={() => setModalOpen(true)}>
          上传教材
        </Button>,
      ]}
    />
  );
}
```

### 3.2 详情页模板

```tsx
export function TextbookDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, loading } = useRequest(() => adminApi.getTextbook(id!));

  return (
    <PageContainer>
      <ProDescriptions<Textbook>
        loading={loading}
        dataSource={data}
        columns={detailColumns}
      />
      {/* 关联章节、知识点等子表 */}
    </PageContainer>
  );
}
```

---

## 4. 路由与权限

### 4.1 RBAC 角色

| 角色 | 说明 | 示例权限 |
|------|------|----------|
| `super_admin` | 超级管理员 | 全部权限 |
| `admin` | 管理员 | 教材管理、内容审核、用户管理 |
| `teacher` | 教师 | 查看/编辑自己创建的教材和任务 |

### 4.2 路由守卫

```tsx
// router/authGuard.tsx
export function AuthGuard({ permission, children }: AuthGuardProps) {
  const user = useAuthStore((s) => s.user);

  if (!user) return <Navigate to="/login" />;
  if (permission && !hasPermission(user.role, permission)) {
    return <NoPermission />;
  }
  return children;
}

// 路由配置
{
  path: '/textbooks',
  element: <AuthGuard permission="textbook:manage"><TextbookList /></AuthGuard>,
}
```

### 4.3 菜单联动

菜单项根据用户角色动态过滤，与路由权限保持一致。

---

## 5. API 请求层

与学生端共享请求模式（参考 `app/DEV-GUIDE.md` §5），差异点：

| 差异 | 学生端 | 管理后台 |
|------|--------|----------|
| 超时 | 30s（LLM 120s） | 60s（导出/批量操作 300s） |
| 限流 | 单用户 120/min | 管理员 300/min |
| Token | 学生 JWT | 管理员 JWT（含 admin/teacher role） |

### 5.1 批量操作

```typescript
// 批量操作使用确认弹窗
const handleBatchDelete = () => {
  Modal.confirm({
    title: `确认删除 ${selectedIds.length} 项？`,
    content: '此操作不可恢复',
    onOk: () => adminApi.batchDelete(selectedIds),
  });
};
```

### 5.2 文件导出

```typescript
// 大文件导出使用 Blob 下载
const handleExport = async () => {
  const blob = await adminApi.exportReport(params);
  downloadBlob(blob, `report_${Date.now()}.xlsx`);
};
```

---

## 6. 样式规范

### 6.1 方案

- **Ant Design 主题定制**（CSS-in-JS / Token）
- **CSS Modules** 用于自定义样式
- 桌面端适配，最小宽度 1280px

### 6.2 主题令牌

```typescript
// antd ConfigProvider theme
const theme = {
  token: {
    colorPrimary: '#4F46E5',
    borderRadius: 6,
    fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
  },
};
```

### 6.3 响应式

- 侧边栏可折叠（小屏 < 1440px 自动折叠）
- 表格水平滚动（列数 > 8 时启用 `scroll={{ x: 1500 }}`）
- 不考虑移动端适配

---

## 7. 日志与错误处理

与学生端日志规范一致（参考 `app/DEV-GUIDE.md` §7），额外约定：

### 7.1 操作审计

管理后台的关键操作（创建/修改/删除）由后端记录审计日志。前端在调用这些 API 时，无需额外记录，但应在 UI 上给出明确的操作反馈：

```typescript
// ✅ 操作反馈
const handleDelete = async (id: string) => {
  await adminApi.deleteTextbook(id);
  message.success('教材已删除');
  actionRef.current?.reload();
};
```

### 7.2 错误提示

```typescript
// 全局 Axios 错误拦截统一 Toast 提示
// 特殊场景在组件内覆盖
try {
  await adminApi.parseTextbook(id);
  message.success('已提交解析任务');
} catch (err) {
  if (err.code === 409031) {
    message.warning('该教材正在解析中，请勿重复提交');
  }
  // 其他错误由全局拦截器处理
}
```

---

## 8. 表格与表单

### 8.1 ProTable 规范

```tsx
const columns: ProColumns<Textbook>[] = [
  { title: '教材名称', dataIndex: 'title', ellipsis: true },
  { title: '学科', dataIndex: 'subject', valueType: 'select', valueEnum: SUBJECT_MAP },
  { title: '解析状态', dataIndex: 'parse_status', valueType: 'select', valueEnum: PARSE_STATUS_MAP },
  { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', sorter: true },
  {
    title: '操作',
    valueType: 'option',
    render: (_, record) => [
      <a key="detail" onClick={() => navigate(`/textbooks/${record.id}`)}>详情</a>,
      <a key="parse" onClick={() => handleParse(record.id)}>解析</a>,
    ],
  },
];
```

### 8.2 ProForm 规范

```tsx
<ProForm<TextbookCreate>
  onFinish={async (values) => {
    await adminApi.createTextbook(values);
    message.success('创建成功');
    return true;
  }}
>
  <ProFormText name="title" label="教材名称" rules={[{ required: true, max: 200 }]} />
  <ProFormSelect name="subject" label="学科" valueEnum={SUBJECT_MAP} rules={[{ required: true }]} />
  <ProFormUploadButton name="file" label="教材文件" max={1} fieldProps={{ accept: '.pdf,.docx,.pptx' }} />
</ProForm>
```

---

## 9. 测试规范

与学生端一致（参考 `app/DEV-GUIDE.md` §8），管理后台额外关注：

- **权限测试**：验证不同角色的路由守卫行为
- **表格测试**：分页、筛选、排序的交互正确性
- **表单测试**：必填校验、格式校验、提交流程

---

## 10. Git 与协作

与学生端一致（参考 `app/DEV-GUIDE.md` §10），Commit scope 使用 `admin`：

```
feat(admin): add textbook management page
fix(admin): fix export timeout for large reports
```

### 10.1 PR 检查清单

- [ ] TypeScript 无报错
- [ ] ESLint 无警告
- [ ] 权限控制正确（对应角色可见/不可见）
- [ ] 表格大数据量下无卡顿（> 100 条测试）
- [ ] 表单校验完整
- [ ] 无 console.log 遗留
- [ ] Ant Design 版本未意外升级

---

*本文件为管理后台开发规范。学生端和家长端另见各自 DEV-GUIDE.md。*
