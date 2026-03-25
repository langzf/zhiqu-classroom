# 用户域数据模型（user-profile）

> 父文档：[README.md](./README.md)

---

## 1. 概述

MVP 阶段专注服务学生群体。支持**手机号验证码登录**和**微信登录**两种方式。家长通过绑定学生账户查看学习报告。

### 实体关系

```
users (1) ──── (0..1) student_profiles     学生扩展信息
users (1) ──── (0..n) user_oauth_bindings  第三方登录绑定（微信）
users (1:guardian) ──── (0..n) guardian_bindings
users (1:student) ──── (0..n) guardian_bindings
```

---

## 2. 表定义

### 2.1 users — 用户主表

所有角色共用一张表，`role` 字段区分身份。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | UUID v7 |
| phone | VARCHAR(20) | NULL | 手机号（手机号登录凭证） |
| nickname | VARCHAR(50) | NOT NULL | 昵称 |
| avatar_url | VARCHAR(500) | NULL | 头像 URL |
| role | VARCHAR(20) | NOT NULL | 角色：`student` / `guardian` / `admin` |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 启用状态 |
| last_login_at | TIMESTAMP | NULL | 最后登录时间 |
| deleted_at | TIMESTAMP | NULL | 软删除标记 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `uniq_users_phone` | phone | UNIQUE | 手机号唯一（`WHERE phone IS NOT NULL AND deleted_at IS NULL`） |
| `idx_users_role` | role | 普通 | 按角色筛选 |

#### 设计说明

- **phone 允许 NULL**：微信登录用户首次注册时可能没有手机号，后续可绑定。手机号登录的用户则必填。
- **部分唯一索引**：`WHERE phone IS NOT NULL AND deleted_at IS NULL`，只对有手机号且未删除的用户做唯一约束。
- **角色精简为 3 种**：MVP 只有学生、家长、管理员。教师角色后续按需扩展。
- **两种登录方式可关联同一用户**：用户先用手机号注册，后绑定微信；或先微信登录，后补绑手机号。通过 phone 或 oauth openid 都能定位到同一个 user。

---

### 2.2 user_oauth_bindings — 第三方登录绑定

存储微信登录凭证。MVP 只接微信，表结构预留扩展能力。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL, FK → users.id | 关联用户 |
| provider | VARCHAR(20) | NOT NULL | 登录方式：`wechat_mp`（小程序）/ `wechat_h5`（公众号） |
| open_id | VARCHAR(128) | NOT NULL | 第三方平台用户标识 |
| union_id | VARCHAR(128) | NULL | 微信 UnionID（跨应用统一标识） |
| access_token | VARCHAR(500) | NULL | 当前有效的 access_token |
| refresh_token | VARCHAR(500) | NULL | 用于刷新的 token |
| token_expires_at | TIMESTAMP | NULL | access_token 过期时间 |
| raw_profile | JSONB | DEFAULT '{}' | 第三方返回的原始用户信息 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `uniq_oauth_provider_openid` | (provider, open_id) | UNIQUE | 同一平台同一用户不可重复 |
| `idx_oauth_user` | user_id | 普通 | 查用户绑定的第三方账号 |
| `idx_oauth_unionid` | union_id | 普通 | 按 UnionID 查找（`WHERE union_id IS NOT NULL`） |

#### 设计说明

- **provider 区分小程序和公众号**：微信小程序（`wechat_mp`）和公众号（`wechat_h5`）的 openid 不同，通过 UnionID 关联。
- **raw_profile**：存微信返回的原始 userInfo，避免信息丢失，后续可从中提取头像、性别等。
- **token 存储**：微信 session_key / access_token 有时效，存储后可用于后续接口调用（如获取手机号）。

---

### 2.3 student_profiles — 学生扩展信息

仅 `role = 'student'` 的用户有此扩展记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL, FK → users.id | 关联用户 |
| grade | VARCHAR(20) | NOT NULL | 年级：`grade_7` ~ `grade_9`（MVP 初中） |
| learning_preferences | JSONB | DEFAULT '{}' | 学习偏好设置 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `uniq_sp_user` | user_id | UNIQUE | 一个用户只有一条学生档案 |
| `idx_sp_grade` | grade | 普通 | 按年级筛选 |

#### `learning_preferences` JSONB 结构示例

```json
{
  "preferred_difficulty": "basic",
  "preferred_game_types": ["quiz", "matching"],
  "daily_study_goal_min": 30
}
```

#### 设计说明

- **精简字段**：去掉了 class_name、school_name、student_no 等班级/学校相关字段。MVP 不做班级管理，后续需要时再加。
- **grade 范围**：MVP 面向初中，`grade_7` / `grade_8` / `grade_9`。后续扩展到小学/高中只需放开枚举值。

---

### 2.4 guardian_bindings — 家长绑定

将家长账户与学生账户建立关联关系。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| guardian_id | UUID | NOT NULL, FK → users.id | 家长用户 ID |
| student_id | UUID | NOT NULL, FK → users.id | 学生用户 ID |
| relationship | VARCHAR(20) | NOT NULL | 关系：`father` / `mother` / `grandparent` / `other` |
| is_primary | BOOLEAN | NOT NULL, DEFAULT false | 是否主要监护人 |
| verified | BOOLEAN | NOT NULL, DEFAULT false | 是否已验证（学生确认） |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `uniq_gb_pair` | (guardian_id, student_id) | UNIQUE | 同一对关系不可重复 |
| `idx_gb_guardian` | guardian_id | 普通 | 查家长绑定的学生 |
| `idx_gb_student` | student_id | 普通 | 查学生绑定的家长 |

#### 设计说明

- **verified 字段**：防止家长随意绑定不相关的学生，需要学生端确认。
- **is_primary**：一个学生可能有多个家长，标记主要联系人用于通知推送。

---

## 3. 登录流程（数据视角）

### 3.1 手机号验证码登录

```
1. 用户输入手机号 → 发送验证码（存 Redis，5分钟有效）
2. 用户提交手机号 + 验证码 → 校验通过
3. 查 users WHERE phone = :phone：
   - 存在 → 更新 last_login_at → 返回 JWT
   - 不存在 → 创建 users（phone 必填）→ 引导选择角色和年级 → 返回 JWT
```

### 3.2 微信登录

```
1. 小程序 wx.login() → 获取 code
2. 后端用 code 换取 openid + session_key
3. 查 user_oauth_bindings WHERE provider + open_id：
   - 存在 → 取 user_id → 返回 JWT
   - 不存在 → 创建 users + user_oauth_bindings → 引导选择角色和年级 → 返回 JWT
4. 如果 role=student 且无 student_profiles → 创建学生档案
```

### 3.3 账号合并

用户先用手机号注册，再用微信登录（或反过来）：
- 微信登录时检测到 UnionID / 手机号已关联已有账户 → 提示合并
- 合并后两种方式登录同一个 user

---

## 4. 典型查询

```sql
-- 手机号登录：查找用户
SELECT * FROM users
WHERE phone = :phone AND deleted_at IS NULL;

-- 微信登录：通过 openid 查找用户
SELECT u.*
FROM user_oauth_bindings ob
JOIN users u ON u.id = ob.user_id
WHERE ob.provider = 'wechat_mp'
  AND ob.open_id = :openid
  AND u.deleted_at IS NULL;

-- 查询家长绑定的所有学生
SELECT u.id, u.nickname, u.avatar_url, sp.grade, gb.relationship
FROM guardian_bindings gb
JOIN users u ON u.id = gb.student_id
JOIN student_profiles sp ON sp.user_id = gb.student_id
WHERE gb.guardian_id = :guardian_user_id
  AND gb.verified = true;

-- 查询某学生的所有家长
SELECT u.id, u.nickname, gb.relationship, gb.is_primary
FROM guardian_bindings gb
JOIN users u ON u.id = gb.guardian_id
WHERE gb.student_id = :student_user_id
  AND gb.verified = true;
```

---

## 5. 后续扩展方向

- 教师角色及扩展表（当需要教师端功能时）
- 班级/学校管理（当需要组织结构管理时）
- 其他第三方登录（user_oauth_bindings 加 provider 枚举值即可）
