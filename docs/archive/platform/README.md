# 平台支撑系统

> zhiqu-classroom 基础设施与运维支撑模块总览  
> 最后更新：2026-03-25

---

## 模块索引

| 文件 | 内容 | 状态 |
|------|------|------|
| [llm-management.md](./llm-management.md) | LLM 模型管理（Provider/Config/路由/熔断） | ✅ |
| [llm-usage.md](./llm-usage.md) | LLM 调用历史 + 用量统计 + 费用预警 | ✅ |
| [config-management.md](./config-management.md) | 配置中心（sys_configs + 分层策略） | ✅ |
| [health-check.md](./health-check.md) | 健康检查 + 就绪检查 + 优雅停机 | ✅ |
| [monitoring.md](./monitoring.md) | 监控告警（Prometheus + Grafana） | ✅ |
| [audit.md](./audit.md) | 审计日志 | ✅ |
| [async-tasks.md](./async-tasks.md) | 异步任务 + 重试策略 | ✅ |
| [security.md](./security.md) | 安全基线 | ✅ |

## 关联文档

- 日志系统详细设计 → [docs/logging/](../logging/README.md)
- 数据模型（平台支撑表） → [docs/data-model/platform-support.md](../data-model/platform-support.md)
- 管理后台 API → [docs/api/admin.md](../api/admin.md)

## 设计原则

1. **MVP 优先**：首期单机部署，保留向上扩展路径
2. **云中立**：不绑定特定云厂商，优先开源/可自部署
3. **渐进增强**：从简单开始（Redis Streams → 后续 RabbitMQ/Kafka）
4. **可观测**：日志 + 指标 + 追踪三位一体
