# 日志分类体系

> 父文档：[README.md](./README.md)

---

## 1. 按功能分类

| 类别 | 说明 | logger 命名 | 输出目标 |
|------|------|-------------|----------|
| **HTTP 访问日志** | 请求入口/出口，状态码、耗时 | `http.access` | stdout → Loki |
| **业务逻辑日志** | 核心业务流程关键节点 | `{service}.{module}` | stdout → Loki |
| **LLM 调用日志** | 模型调用详情（provider/token/cost） | `llm.call` | stdout → Loki + DB |
| **异步任务日志** | 任务生命周期 | `task.{task_name}` | stdout → Loki |
| **安全审计日志** | 管理操作、权限变更 | `audit` | stdout → Loki + DB |
| **系统运维日志** | 健康检查、连接池、缓存命中 | `system.{component}` | stdout → Loki |

## 2. logger 命名规范

```
格式：{service_or_category}.{module}.{sub_module}

示例：
  http.access                     ← HTTP 请求日志
  content_engine.textbook_parser  ← 教材解析模块
  content_engine.knowledge        ← 知识点抽取
  learning_engine.task_assign     ← 任务分配
  llm.call                        ← LLM 调用（统一）
  llm.routing                     ← LLM 路由决策
  task.textbook_parse             ← 异步任务：教材解析
  task.game_generate              ← 异步任务：游戏生成
  audit                           ← 审计操作
  system.health                   ← 健康检查
  system.db_pool                  ← 数据库连接池
  system.redis                    ← Redis 连接
```

## 3. 按持久化目标分类

| 日志类型 | stdout | Loki | 数据库 | 保留时间 |
|----------|--------|------|--------|----------|
| HTTP 访问日志 | ✅ | ✅ | ❌ | 30天 |
| 业务逻辑日志 | ✅ | ✅ | ❌ | 30天 |
| LLM 调用日志 | ✅ | ✅ | ✅ `llm_call_logs` | Loki 30天 / DB 6个月 |
| 异步任务日志 | ✅ | ✅ | ✅ `task_executions` | Loki 30天 / DB 6个月 |
| 审计日志 | ✅ | ✅ | ✅ `audit_logs` | Loki 30天 / DB 永久 |
| 系统运维日志 | ✅ | ✅ | ❌ | 14天 |
