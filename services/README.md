# Services 规划（v0）

## 子系统职责
- `api-gateway`: 统一API入口、鉴权、限流、路由聚合。
- `content-engine`: 教材解析、知识点抽取、知识点检索。
- `media-generation`: 生成AI游戏配置、视频脚本、练习内容。
- `learning-orchestrator`: 课后任务编排、任务状态流转（首期主流程服务）。
- `user-profile`: 用户、学生档案、家长关系、权限。
- `analytics-reporting`: 学习数据统计、报表与效果分析。
- `notification`: 消息触达（站内信、短信/推送预留）。
- `shared`: 公共库与通用协议（DTO、错误码、工具函数）。

## 分期建议
- 首期优先：`api-gateway`、`content-engine`、`media-generation`、`learning-orchestrator`、`user-profile`
- 次期补齐：`analytics-reporting`、`notification`
