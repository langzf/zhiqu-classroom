# api-gateway

## 职责
- 统一 HTTP API 入口。
- 鉴权、限流、请求路由、聚合响应。

## 对外接口（示例）
- `POST /v1/auth/login`
- `GET /v1/textbooks/:id`
- `POST /v1/tasks/:id/start`

## 上游调用
- `user-profile`
- `content-engine`
- `media-generation`
- `learning-orchestrator`
- `analytics-reporting`（后期）

## 数据归属
- 无业务主数据归属，仅维护网关配置与审计日志。

## 非职责
- 不直接实现业务规则。
- 不持久化核心教学业务数据。
