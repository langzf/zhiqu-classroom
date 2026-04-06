# user-profile

## 职责
- 用户账号、角色、组织关系管理。
- 学生-家长绑定关系。
- 权限控制策略（RBAC 基础）。

## 对外接口（示例）
- `POST /internal/users`
- `GET /internal/users/:id`
- `POST /internal/students/:id/guardians/bind`

## 数据归属
- 用户基础资料。
- 关系映射（学生/家长/教师）。
- 认证与权限元数据。

## 非职责
- 不负责学习内容生产与任务编排。
