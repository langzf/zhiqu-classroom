# LogQL 查询与 Grafana 面板

> 父文档：[README.md](./README.md)

---

## 1. 常用 LogQL 查询

### 按 trace_id 追踪完整链路

```logql
{service=~".+"} | json | trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### 查看某服务的错误日志

```logql
{service="content-engine", level="ERROR"} | json
```

### HTTP 慢请求（>1s）

```logql
{service=~".+"} | json | logger="http.access" | message="HTTP 请求完成" | duration_ms > 1000
```

### LLM 调用失败

```logql
{service=~".+"} | json | logger="llm.call" | message="LLM 调用失败"
```

### 特定用户的操作日志

```logql
{service=~".+"} | json | user_id="user-uuid-xxx"
```

### 熔断事件

```logql
{service=~".+"} | json | logger="llm.routing" | message=~"熔断.*"
```

### 认证失败

```logql
{service=~".+"} | json | message=~"登录失败|权限校验失败|Token 已过期"
```

### 异步任务失败

```logql
{service=~".+"} | json | logger=~"task\\..+" | level="ERROR"
```

## 2. 指标查询（LogQL Metrics）

### 各服务每分钟错误率

```logql
sum by (service) (
  rate({service=~".+"} | json | level="ERROR" [5m])
)
```

### HTTP P99 延迟

```logql
quantile_over_time(0.99,
  {service=~".+"} | json | logger="http.access" | message="HTTP 请求完成"
  | unwrap duration_ms [5m]
) by (service)
```

### LLM 每分钟调用量

```logql
sum by (llm_provider, llm_model) (
  rate({service=~".+"} | json | logger="llm.call" | message="LLM 调用成功" [5m])
)
```

### LLM 每小时费用趋势

```logql
sum by (llm_provider) (
  sum_over_time({service=~".+"} | json | logger="llm.call" | message="LLM 调用成功"
  | unwrap cost_yuan [1h])
)
```

## 3. Grafana Dashboard 规划

### Dashboard 1: 服务总览

| Panel | 类型 | 数据源 |
|-------|------|--------|
| 请求量/分钟 | Time Series | LogQL rate |
| 错误率 | Stat/Gauge | LogQL rate(ERROR) / rate(total) |
| P50/P95/P99 延迟 | Time Series | LogQL quantile |
| 状态码分布 | Pie Chart | LogQL by status_code |
| 最近错误列表 | Logs Panel | LogQL level=ERROR |

### Dashboard 2: LLM 监控

| Panel | 类型 | 数据源 |
|-------|------|--------|
| 调用量/分钟 by provider | Time Series | LogQL rate |
| 平均延迟 by model | Time Series | LogQL avg |
| 费用趋势 | Time Series | LogQL sum cost_yuan |
| 成功率 | Gauge | LogQL rate(success) / rate(total) |
| 降级/熔断事件 | Alert List | LogQL |
| Token 消耗趋势 | Time Series | LogQL sum tokens |

### Dashboard 3: 异步任务

| Panel | 类型 | 数据源 |
|-------|------|--------|
| 任务完成量/失败量 | Time Series | LogQL rate |
| 平均执行耗时 | Time Series | LogQL avg execution_ms |
| 重试分布 | Bar Chart | LogQL by retry_count |
| 队列积压（如有 Redis metrics） | Gauge | Prometheus |

### Dashboard 4: 安全审计

| Panel | 类型 | 数据源 |
|-------|------|--------|
| 登录成功/失败趋势 | Time Series | LogQL |
| 权限拒绝事件 | Logs Panel | LogQL |
| 管理操作日志 | Table | LogQL audit |
