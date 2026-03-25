# 日志系统设计

> zhiqu-classroom 全服务统一日志规范  
> 最后更新：2026-03-25

---

## 模块索引

| 文件 | 内容 | 行数 |
|------|------|------|
| [classification.md](./classification.md) | 日志分类体系 + logger 命名规范 | ~80 |
| [levels.md](./levels.md) | 日志级别定义 + 使用规则 + 动态调整 | ~100 |
| [format.md](./format.md) | JSON Schema + 字段定义 + message 规范 | ~180 |
| [tracing.md](./tracing.md) | 链路追踪 + contextvars + span 机制 | ~130 |
| [sanitization.md](./sanitization.md) | 敏感字段脱敏规则 + 代码实现 | ~100 |
| [scenarios.md](./scenarios.md) | HTTP / 数据库 / 外部服务 / 认证鉴权日志模板 | ~180 |
| [llm-logging.md](./llm-logging.md) | LLM 调用专项日志（路由/调用/熔断/入库） | ~160 |
| [async-task-logging.md](./async-task-logging.md) | 异步任务 + 定时任务日志 | ~100 |
| [collection.md](./collection.md) | 采集架构（Docker → Promtail → Loki → Grafana） | ~120 |
| [query-dashboard.md](./query-dashboard.md) | LogQL 查询模板 + Grafana 面板规划 | ~100 |
| [retention.md](./retention.md) | 轮转保留策略 + 分区 + 冷归档 | ~100 |
| [code-review.md](./code-review.md) | 日志编写规约（Code Review 检查项） | ~80 |

---

## 设计目标

| 目标 | 说明 |
|------|------|
| **全局统一** | 所有服务使用 structlog + JSON 格式 + 同一上下文注入机制 |
| **结构化** | 全量 JSON 输出，每个字段有明确语义，便于机器解析 |
| **链路贯通** | trace_id + span_id 串联完整请求链路，跨服务可追溯 |
| **自动化** | 中间件 + 装饰器自动注入上下文，业务代码零改动 |
| **安全脱敏** | 敏感信息在写入前自动脱敏 |
| **可观测** | 与 Prometheus 指标、Grafana 面板协同 |
| **成本可控** | 合理的级别管控 + 采样策略，避免日志爆炸 |

## 设计原则

1. 日志是基础设施，不是事后补丁——架构设计时就规划好
2. 结构化 > 自由文本——永远用 KV 传参，不要拼接字符串
3. 上下文自动注入 > 手动传递——开发者不需要关心 trace_id 怎么来的
4. 脱敏在写入前完成——日志存储层看到的已经是安全数据
5. 开发环境可读 > JSON——本地开发用 ConsoleRenderer，线上用 JSON
6. 宁可多记不可漏记——关键节点必须有日志，但要控制粒度

## 强制规则（全员遵守）

| 规则 | 说明 |
|------|------|
| 🚫 禁止 `print()` | 所有输出走 structlog |
| 🚫 禁止 INFO 循环日志 | 循环内日志用 DEBUG |
| 🚫 禁止明文密钥 | 日志中不能出现未脱敏的 key/token |
| ✅ 每请求至少 2 条 INFO | 入口 + 出口 |
| ✅ 异常必须 ERROR + traceback | `exc_info=True` |
| ✅ KV 格式传参 | `logger.info("消息", key=value)` |
