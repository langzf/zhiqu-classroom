# 服务契约总览（v0）

## 首期核心链路
1. `content-engine` 解析教材并生成知识点。
2. `media-generation` 基于知识点生成游戏/视频脚本/练习。
3. `learning-orchestrator` 发布课后任务并跟踪完成状态。
4. `analytics-reporting` 汇总基础效果指标（可后接）。

## 同步接口原则
- 外部客户端仅访问 `api-gateway`。
- 服务间调用使用内部接口 `/internal/*`。
- 接口统一返回：`code`, `message`, `data`, `request_id`。

## 异步事件原则
- 事件命名：`domain.entity.action`（如 `task.completed`）。
- 每个事件必须包含：`event_id`, `event_name`, `occurred_at`, `producer`, `payload`。
- 消费方必须实现幂等处理。

## 数据边界原则
- 谁创建、谁拥有主写权限。
- 跨服务只读通过 API 或订阅事件投影。
- 禁止跨服务直连数据库。
