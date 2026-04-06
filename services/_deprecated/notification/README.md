# notification

## 职责
- 统一消息触达（站内信/Push/短信预留）。
- 模板化通知发送与重试。

## 对外接口（示例）
- `POST /internal/notify/send`
- `POST /internal/notify/batch`

## 事件输入
- `task.published`
- `task.reminder.required`
- `weekly.report.ready`

## 数据归属
- 发送记录、回执状态、重试队列。

## 非职责
- 不负责业务决策（是否发送由上游决定）。
