# User & Auth API — 用户与认证

> 父文档：[README.md](./README.md) | 数据模型：[data-model.md](../data-model.md) user-profile schema  
> 服务前缀：`/api/v1`

---

## 接口总览

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| POST | `/auth/sms/send` | 🌐 public | 发送短信验证码 |
| POST | `/auth/sms/verify` | 🌐 public | 短信验证码登录/注册 |
| POST | `/auth/refresh` | 🌐 public | 刷新 Token |
| POST | `/auth/logout` | 👤 all | 退出登录 |
| GET | `/users/me` | 👤 all | 当前用户信息 |
| PATCH | `/users/me` | 👤 all | 更新个人信息 |
| POST | `/users/me/avatar` | 👤 all | 上传头像 |
| GET | `/users/me/children` | 👤 guardian | 家长 — 绑定的学生列表 |
| POST | `/users/me/children/bind` | 👤 guardian | 家长 — 绑定学生 |
| DELETE | `/users/me/children/:studentId` | 👤 guardian | 家长 — 解绑学生 |
| GET | `/admin/users` | 🛡️ admin | 用户列表 |
| GET | `/admin/users/:id` | 🛡️ admin | 用户详情 |
| PATCH | `/admin/users/:id` | 🛡️ admin | 更新用户 |
| PATCH | `/admin/users/:id/status` | 🛡️ admin | 启用/禁用用户 |
| GET | `/admin/students` | 🛡️ admin/teacher | 学生列表 |
| POST | `/admin/students/import` | 🛡️ admin | 批量导入学生 |

---

## 1. 认证

### 1.1 发送短信验证码

```
POST /api/v1/auth/sms/send
```

**Request Body**

```json
{
  "phone": "13800138000",
  "scene": "login"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✅ | 手机号（中国大陆 11 位） |
| scene | string | | `login`（默认）/ `bind` |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "ttl_sec": 300,
    "next_send_after_sec": 60
  }
}
```

> 频率限制：同一手机号 60s 内不可重发；同一 IP 每小时最多 10 次。

### 1.2 短信验证码登录/注册

```
POST /api/v1/auth/sms/verify
```

验证通过后，若手机号未注册则自动创建用户。

**Request Body**

```json
{
  "phone": "13800138000",
  "code": "123456",
  "device_id": "device-uuid"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | ✅ | 手机号 |
| code | string | ✅ | 6 位验证码 |
| device_id | string | | 设备标识，用于多端管理 |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user": {
      "id": "user-uuid",
      "phone": "138****8000",
      "nickname": null,
      "role": "student",
      "is_new": true
    }
  }
}
```

> `is_new = true` 时前端引导完善个人信息。

### 1.3 刷新 Token

```
POST /api/v1/auth/refresh
```

**Request Body**

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g..."
}
```

**Response** `200` — 返回新的 `access_token` + `refresh_token`（旧 refresh_token 立即失效）。

### 1.4 退出登录

```
POST /api/v1/auth/logout
```

**Headers**: `Authorization: Bearer <access_token>`

将当前 access_token 和 refresh_token 加入黑名单。

**Response** `200`

```json
{ "code": 0, "message": "ok", "data": null }
```

---

## 2. 个人信息

### 2.1 当前用户信息

```
GET /api/v1/users/me
```

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "user-uuid",
    "phone": "138****8000",
    "nickname": "小明同学",
    "avatar_url": "https://oss.example.com/avatars/user-uuid.jpg",
    "role": "student",
    "is_active": true,
    "profile": {
      "grade": "grade_7",
      "class_name": "3班",
      "school_name": "北京市第一中学",
      "student_no": "2026070301"
    },
    "created_at": "...",
    "last_login_at": "..."
  }
}
```

> `profile` 字段根据角色不同结构不同：
> - **student** → `grade`, `class_name`, `school_name`, `student_no`
> - **teacher** → `subject`, `title`, `school_name`
> - **guardian** → `children_count`

### 2.2 更新个人信息

```
PATCH /api/v1/users/me
```

**Request Body**

```json
{
  "nickname": "小明同学",
  "profile": {
    "grade": "grade_7",
    "class_name": "3班",
    "school_name": "北京市第一中学"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| nickname | string | 昵称（2-20 字） |
| profile | object | 角色相关信息 |

**Response** `200` — 返回更新后的用户对象。

### 2.3 上传头像

```
POST /api/v1/users/me/avatar
```

**Request**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | file | 图片文件（jpg/png，最大 5MB） |

**Response** `200`

```json
{
  "code": 0,
  "message": "ok",
  "data": { "avatar_url": "https://oss.example.com/avatars/user-uuid.jpg" }
}
```
