# MVP API 接口定义（v1.0）

> 适用范围：zhiqu-classroom MVP 阶段
> 基础路径：`/api/v1`
> 认证方式：Bearer JWT（除登录/注册外所有接口）
> 响应格式：统一 JSON envelope

---

## 0. 通用约定

### 0.1 统一响应格式

**成功：**
```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

**分页成功：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [ ... ],
    "total": 120,
    "page": 1,
    "page_size": 20
  }
}
```

**失败：**
```json
{
  "code": 40001,
  "message": "手机号格式不正确",
  "data": null
}
```

### 0.2 错误码规范

| 范围 | 归属 |
|------|------|
| 40000-40099 | 通用参数错误 |
| 40100-40199 | 认证/权限错误 |
| 41000-41099 | user-profile 业务错误 |
| 42000-42099 | content-engine 业务错误 |
| 43000-43099 | media-generation 业务错误 |
| 44000-44099 | learning-orchestrator 业务错误 |
| 45000-45099 | analytics-reporting 业务错误 |
| 50000-50099 | 服务内部错误 |

### 0.3 通用请求头

| Header | 说明 |
|--------|------|
| `Authorization` | `Bearer <access_token>` |
| `X-Request-ID` | 请求追踪 ID（客户端生成，服务端透传） |
| `X-Device-ID` | 设备标识（用于限流/审计） |

### 0.4 分页参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码（从 1 开始） |
| page_size | int | 20 | 每页条数（最大 100） |

### 0.5 角色标记

- 🔓 公开（无需认证）
- 👤 所有登录用户
- 🎓 学生
- 👨‍👩‍👧 家长
- 🏫 教师
- 🔑 管理员

---

## 1. 认证接口（Auth）

### 1.1 发送短信验证码

```
POST /api/v1/auth/sms/send  🔓
```

**Request：**
```json
{
  "phone": "13800138000",
  "purpose": "login"
}
```
> purpose: `login` | `register` | `reset`

**Response：**
```json
{
  "code": 0,
  "data": {
    "expire_sec": 300,
    "cooldown_sec": 60
  }
}
```

| 错误码 | 说明 |
|--------|------|
| 40001 | 手机号格式不正确 |
| 40002 | 发送过于频繁 |

---

### 1.2 短信验证码登录/注册

```
POST /api/v1/auth/sms/verify  🔓
```

**Request：**
```json
{
  "phone": "13800138000",
  "code": "123456",
  "role": "student",
  "nickname": "小明"
}
```
> `role` 和 `nickname` 仅首次注册时必填

**Response：**
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "abc...",
    "expires_in": 7200,
    "is_new_user": true,
    "user": {
      "id": "550e8400-...",
      "phone": "138****8000",
      "nickname": "小明",
      "role": "student",
      "avatar_url": null
    }
  }
}
```

| 错误码 | 说明 |
|--------|------|
| 40101 | 验证码错误或已过期 |
| 40102 | 该手机号已被禁用 |

---

### 1.3 刷新 Token

```
POST /api/v1/auth/token/refresh  🔓
```

**Request：**
```json
{
  "refresh_token": "abc..."
}
```

**Response：**
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "new_abc...",
    "expires_in": 7200
  }
}
```

| 错误码 | 说明 |
|--------|------|
| 40103 | refresh_token 无效或已过期 |

---

### 1.4 退出登录

```
POST /api/v1/auth/logout  👤
```

**Request：**
```json
{
  "refresh_token": "abc..."
}
```

**Response：**
```json
{ "code": 0, "message": "ok", "data": null }
```

---

### 1.5 微信小程序登录

```
POST /api/v1/auth/wechat/mini  🔓
```

**Request：**
```json
{
  "js_code": "xxx",
  "encrypted_data": "...",
  "iv": "..."
}
```
> `encrypted_data` + `iv` 可选，用于获取手机号

**Response：** 同 1.2

---

## 2. 用户接口（User Profile）

### 2.1 获取当前用户信息

```
GET /api/v1/users/me  👤
```

**Response：**
```json
{
  "code": 0,
  "data": {
    "id": "550e8400-...",
    "phone": "138****8000",
    "nickname": "小明",
    "role": "student",
    "avatar_url": "https://...",
    "status": "active",
    "created_at": "2026-03-01T10:00:00Z",
    "profile": {
      "grade": "grade_7",
      "learning_preferences": {
        "preferred_difficulty": "basic",
        "preferred_game_types": ["quiz", "matching"],
        "daily_study_goal_min": 30
      }
    }
  }
}
```

---

### 2.2 更新当前用户信息

```
PATCH /api/v1/users/me  👤
```

**Request：**
```json
{
  "nickname": "小明同学",
  "avatar_url": "https://..."
}
```

---

### 2.3 更新学生档案

```
PATCH /api/v1/users/me/student-profile  🎓
```

**Request：**
```json
{
  "grade": "grade_8",
  "learning_preferences": {
    "preferred_difficulty": "intermediate",
    "daily_study_goal_min": 45
  }
}
```

---

### 2.4 生成绑定码（学生发起）

```
POST /api/v1/users/me/guardian-bindcode  🎓
```

**Response：**
```json
{
  "code": 0,
  "data": {
    "bind_code": "A3K8X2",
    "expire_at": "2026-03-25T15:00:00Z"
  }
}
```

---

### 2.5 家长绑定学生

```
POST /api/v1/users/me/guardian-bindings  👨‍👩‍👧
```

**Request：**
```json
{
  "bind_code": "A3K8X2",
  "relation": "mother"
}
```

**Response：**
```json
{
  "code": 0,
  "data": {
    "binding_id": "...",
    "student": {
      "id": "...",
      "nickname": "小明",
      "grade": "grade_7"
    }
  }
}
```

| 错误码 | 说明 |
|--------|------|
| 41001 | 绑定码无效或已过期 |
| 41002 | 已绑定该学生 |

---

### 2.6 获取绑定的学生列表（家长）

```
GET /api/v1/users/me/guardian-bindings  👨‍👩‍👧
```

**Response：**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "binding_id": "...",
        "relation": "mother",
        "student": {
          "id": "...",
          "nickname": "小明",
          "grade": "grade_7",
          "avatar_url": "..."
        }
      }
    ]
  }
}
```

---

### 2.7 用户管理（管理后台）

```
GET    /api/v1/admin/users              🔑  列表（分页+筛选）
GET    /api/v1/admin/users/:id          🔑  详情
PATCH  /api/v1/admin/users/:id          🔑  编辑
PATCH  /api/v1/admin/users/:id/status   🔑  启用/禁用
```

**GET 筛选参数：** `role`, `status`, `keyword`（手机号/昵称模糊搜索）, `page`, `page_size`

---

_后续接口（教材知识点、内容生成、学习编排、统计报表、通知）将在 Part 2-5 中补充。_
