# 消息通知

> Schema: `notification`
> 最后更新: 2026-03-25

---

## 概述

消息通知模块提供多渠道触达能力（短信、微信模板消息、站内信），支持模板化内容管理和用户偏好设置。
通知由业务事件驱动，通过 Redis Streams 消费触发。

### 支持渠道

| 渠道 | 说明 | 状态 |
|------|------|------|
| `sms` | 阿里云短信 | MVP ✅ |
| `wechat` | 微信模板消息 / 订阅消息 | MVP ✅ |
| `in_app` | 站内信（客户端轮询 / WebSocket） | MVP ✅ |
| `email` | 邮件 | 后期规划 |
| `push` | APP 推送（极光 / 个推） | 后期规划 |

---

## 1. notification_templates（通知模板）

### DDL

```sql
CREATE TABLE notification.notification_templates (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    template_code   VARCHAR(100)    NOT NULL,
    template_name   VARCHAR(200)    NOT NULL,
    channel         VARCHAR(20)     NOT NULL,
    event_trigger   VARCHAR(100)    NULL,
    title_template  VARCHAR(500)    NULL,
    body_template   TEXT            NOT NULL,
    variables       JSONB           NOT NULL DEFAULT '[]',
    sms_sign_name   VARCHAR(50)     NULL,
    sms_template_id VARCHAR(50)     NULL,
    wx_template_id  VARCHAR(100)    NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMP       NULL
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 模板 ID |
| template_code | VARCHAR(100) | NOT NULL | 模板编码，如 `task_assigned`、`report_ready`、`sms_verify` |
| template_name | VARCHAR(200) | NOT NULL | 模板名称（管理后台显示） |
| channel | VARCHAR(20) | NOT NULL | 通知渠道：`sms` / `wechat` / `in_app` / `email` |
| event_trigger | VARCHAR(100) | NULL | 触发事件名，如 `task.assigned`、`report.ready`（NULL 表示手动触发） |
| title_template | VARCHAR(500) | NULL | 标题模板（站内信和微信使用，短信无标题） |
| body_template | TEXT | NOT NULL | 内容模板，使用 `{{variable}}` 占位符 |
| variables | JSONB | NOT NULL | 模板变量定义 `[{"name": "student_name", "type": "string", "required": true}]` |
| sms_sign_name | VARCHAR(50) | NULL | 短信签名（仅 sms 渠道） |
| sms_template_id | VARCHAR(50) | NULL | 短信服务商模板 ID（仅 sms 渠道） |
| wx_template_id | VARCHAR(100) | NULL | 微信模板 ID（仅 wechat 渠道） |
| is_active | BOOLEAN | NOT NULL | 是否启用 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |
| deleted_at | TIMESTAMP | NULL | 软删除 |

### 索引

```sql
-- 模板编码 + 渠道 唯一
CREATE UNIQUE INDEX uniq_notification_templates_code_channel
    ON notification.notification_templates (template_code, channel)
    WHERE deleted_at IS NULL;

-- 按事件触发查
CREATE INDEX idx_notification_templates_event
    ON notification.notification_templates (event_trigger)
    WHERE event_trigger IS NOT NULL AND deleted_at IS NULL;
```

### 初始数据示例

```sql
INSERT INTO notification.notification_templates
    (template_code, template_name, channel, event_trigger, title_template, body_template, variables, sms_sign_name, sms_template_id)
VALUES
-- 短信验证码
('sms_verify', '短信验证码', 'sms', NULL,
 NULL,
 '您的验证码是{{code}}，5分钟内有效。',
 '[{"name": "code", "type": "string", "required": true}]',
 '知趣课堂', 'SMS_000001'),

-- 任务布置通知（站内信）
('task_assigned', '任务布置通知', 'in_app', 'task.assigned',
 '你有新的学习任务',
 '{{teacher_name}}老师布置了新任务「{{task_title}}」，截止时间 {{deadline}}。',
 '[{"name": "teacher_name", "type": "string", "required": true}, {"name": "task_title", "type": "string", "required": true}, {"name": "deadline", "type": "string", "required": true}]',
 NULL, NULL),

-- 学习报告（微信）
('report_ready', '学习报告生成通知', 'wechat', 'report.ready',
 '学习报告已生成',
 '{{student_name}}同学{{period}}的学习报告已生成，点击查看详情。',
 '[{"name": "student_name", "type": "string", "required": true}, {"name": "period", "type": "string", "required": true}]',
 NULL, NULL);
```

---

## 2. notification_logs（发送记录）

### DDL

```sql
CREATE TABLE notification.notification_logs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID            NULL,           -- ref: notification_templates.id
    template_code   VARCHAR(100)    NOT NULL,
    channel         VARCHAR(20)     NOT NULL,
    user_id         UUID            NOT NULL,       -- ref: users.id
    recipient       VARCHAR(200)    NOT NULL,
    title           VARCHAR(500)    NULL,
    body            TEXT            NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',
    vendor_msg_id   VARCHAR(200)    NULL,
    error_code      VARCHAR(50)     NULL,
    error_message   TEXT            NULL,
    retry_count     INT             NOT NULL DEFAULT 0,
    sent_at         TIMESTAMP       NULL,
    read_at         TIMESTAMP       NULL,
    metadata        JSONB           NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT now()
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| template_id | UUID | NULL | 关联 notification_templates.id |
| template_code | VARCHAR(100) | NOT NULL | 冗余模板编码（便于统计） |
| channel | VARCHAR(20) | NOT NULL | 通知渠道 |
| user_id | UUID | NOT NULL | 接收用户 — ref: users.id |
| recipient | VARCHAR(200) | NOT NULL | 接收地址：手机号 / openid / user_id |
| title | VARCHAR(500) | NULL | 渲染后的标题 |
| body | TEXT | NOT NULL | 渲染后的内容 |
| status | VARCHAR(20) | NOT NULL | 发送状态 |
| vendor_msg_id | VARCHAR(200) | NULL | 渠道方返回的消息 ID（用于状态回调） |
| error_code | VARCHAR(50) | NULL | 失败错误码 |
| error_message | TEXT | NULL | 失败错误信息 |
| retry_count | INT | NOT NULL | 已重试次数 |
| sent_at | TIMESTAMP | NULL | 实际发送时间 |
| read_at | TIMESTAMP | NULL | 已读时间（仅站内信） |
| metadata | JSONB | NULL | 附加信息（事件来源、业务上下文等） |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

### 索引

```sql
-- 按用户查通知历史（站内信列表）
CREATE INDEX idx_notification_logs_user
    ON notification.notification_logs (user_id, created_at DESC);

-- 按用户 + 渠道 + 未读（站内信未读计数）
CREATE INDEX idx_notification_logs_user_unread
    ON notification.notification_logs (user_id, channel)
    WHERE read_at IS NULL AND status = 'delivered';

-- 按状态查（重试队列）
CREATE INDEX idx_notification_logs_status
    ON notification.notification_logs (status, created_at)
    WHERE status IN ('pending', 'failed');

-- 按模板统计
CREATE INDEX idx_notification_logs_template
    ON notification.notification_logs (template_code, status, created_at DESC);

-- 供应商消息 ID 回调查找
CREATE INDEX idx_notification_logs_vendor
    ON notification.notification_logs (vendor_msg_id)
    WHERE vendor_msg_id IS NOT NULL;
```

### 状态机

```
┌─────────┐   ┌───────────┐   ┌───────────┐
│ pending  │──►│  sending  │──►│ delivered │
└─────────┘   └─────┬─────┘   └─────┬─────┘
                    │                │
                    ▼                ▼ (站内信)
               ┌─────────┐    ┌─────────┐
               │ failed   │    │  read   │
               └─────────┘    └─────────┘
```

| 状态 | 说明 |
|------|------|
| `pending` | 等待发送 |
| `sending` | 发送中（已提交到渠道方） |
| `delivered` | 已送达 |
| `failed` | 发送失败 |
| `read` | 已读（仅站内信） |

---

## 3. notification_preferences（用户通知偏好）

### DDL

```sql
CREATE TABLE notification.notification_preferences (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL,       -- ref: users.id
    channel         VARCHAR(20)     NOT NULL,
    is_enabled      BOOLEAN         NOT NULL DEFAULT TRUE,
    quiet_start     TIME            NULL,
    quiet_end       TIME            NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT now()
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| user_id | UUID | NOT NULL | 用户 — ref: users.id |
| channel | VARCHAR(20) | NOT NULL | 通知渠道 |
| is_enabled | BOOLEAN | NOT NULL | 是否接收该渠道通知 |
| quiet_start | TIME | NULL | 免打扰开始时间（如 22:00） |
| quiet_end | TIME | NULL | 免打扰结束时间（如 08:00） |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

### 索引

```sql
-- 用户 + 渠道 唯一
CREATE UNIQUE INDEX uniq_notification_pref_user_channel
    ON notification.notification_preferences (user_id, channel);
```

---

## 枚举值

| 枚举名 | 值 | 使用字段 |
|--------|-----|----------|
| channel | `sms`, `wechat`, `in_app`, `email`, `push` | 通用渠道字段 |
| notification_status | `pending`, `sending`, `delivered`, `failed`, `read` | notification_logs.status |

---

## 事件驱动流程

```
业务事件 (Redis Stream)
    │  stream:task.completed
    │  stream:report.ready
    ▼
Notification Worker
    ├── 查 notification_templates (event_trigger 匹配)
    ├── 查 notification_preferences (用户是否接收 + 免打扰)
    ├── 渲染模板 → 生成 body
    ├── INSERT notification_logs (status=pending)
    │
    ├── SMS → 阿里云短信 API
    ├── WeChat → 微信模板消息 API
    ├── In-App → 直接 INSERT (status=delivered)
    │
    └── 回调/轮询更新 status
```

---

## 使用场景

### 查询用户站内信列表（分页）

```sql
SELECT id, title, body, status, read_at, created_at
FROM notification.notification_logs
WHERE user_id = '550e8400-...'
  AND channel = 'in_app'
  AND status IN ('delivered', 'read')
ORDER BY created_at DESC
LIMIT 20 OFFSET 0;
```

### 未读消息计数

```sql
SELECT COUNT(*)
FROM notification.notification_logs
WHERE user_id = '550e8400-...'
  AND channel = 'in_app'
  AND status = 'delivered'
  AND read_at IS NULL;
```

### 模板发送成功率统计

```sql
SELECT template_code, channel,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
       COUNT(*) FILTER (WHERE status = 'failed') AS failed,
       ROUND(
           COUNT(*) FILTER (WHERE status = 'delivered')::decimal /
           NULLIF(COUNT(*), 0) * 100, 1
       ) AS delivery_rate
FROM notification.notification_logs
WHERE created_at > now() - INTERVAL '7 days'
GROUP BY template_code, channel
ORDER BY total DESC;
```

### 免打扰检查

```sql
-- 应用层伪代码
SELECT is_enabled, quiet_start, quiet_end
FROM notification.notification_preferences
WHERE user_id = :user_id AND channel = :channel;

-- 如果 is_enabled = false → 跳过
-- 如果当前时间在 [quiet_start, quiet_end] 内 → 延迟发送
```
