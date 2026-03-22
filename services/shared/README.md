# shared

## 职责
- 公共 DTO/错误码规范。
- 通用工具库（日志、追踪、配置读取）。
- 服务间契约定义（OpenAPI/事件Schema）。

## 目录建议
- `contracts/http/`
- `contracts/events/`
- `libs/`

## 约束
- `shared` 只放通用能力，不放业务实现。
