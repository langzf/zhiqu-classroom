# 监控告警

> 父文档：[README.md](./README.md)

---

## 1. 概述

基于 Prometheus + Grafana 构建可观测体系，覆盖应用指标、基础设施指标和业务指标。MVP 阶段轻量部署，保留向 K8s 原生监控演进的路径。

```
┌─────────────┐   /metrics   ┌────────────┐         ┌──────────┐
│   Service    │ ◄─────────── │ Prometheus │ ───────► │ Grafana  │
│ (FastAPI)    │              │  (scrape)  │         │ 看板/告警 │
└─────────────┘              └────────────┘         └──────────┘
       │                           │
       │  push                     │  rules
       ▼                           ▼
  Redis/PG Exporter         AlertManager → 飞书/邮件
```

## 2. 指标分层

### 2.1 应用指标（自定义）

使用 `prometheus-fastapi-instrumentator` 自动采集 + 自定义业务指标：

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `http_requests_total` | Counter | method, path, status | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | method, path | 请求延迟分布 |
| `http_requests_in_progress` | Gauge | method | 当前并发请求数 |
| `llm_call_total` | Counter | task_type, model, status | LLM 调用次数 |
| `llm_call_duration_seconds` | Histogram | task_type, model | LLM 调用延迟 |
| `llm_call_cost_yuan_total` | Counter | model | LLM 累计费用 |
| `llm_circuit_open` | Gauge | model | 熔断器状态（0=关/1=开） |
| `task_queue_length` | Gauge | queue_name | 任务队列长度 |
| `task_processing_duration_seconds` | Histogram | task_type | 任务处理耗时 |
| `active_users_total` | Gauge | role | 当前活跃用户数 |

### 2.2 基础设施指标

| 组件 | Exporter | 关键指标 |
|------|----------|----------|
| PostgreSQL | `postgres_exporter` | 连接数、慢查询数、表大小、锁等待 |
| Redis | `redis_exporter` | 内存使用、连接数、命中率、key 数量 |
| MinIO | 内置 `/minio/v2/metrics` | 存储用量、请求量、带宽 |
| Node | `node_exporter` | CPU、内存、磁盘、网络 |

## 3. 指标埋点

```python
# services/shared/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# LLM 调用指标
llm_call_total = Counter(
    "llm_call_total",
    "LLM 调用总数",
    ["task_type", "model", "status"],
)

llm_call_duration = Histogram(
    "llm_call_duration_seconds",
    "LLM 调用延迟",
    ["task_type", "model"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)

llm_cost_total = Counter(
    "llm_call_cost_yuan_total",
    "LLM 累计费用（元）",
    ["model"],
)

llm_circuit_open = Gauge(
    "llm_circuit_open",
    "LLM 熔断器状态",
    ["model"],
)

task_queue_length = Gauge(
    "task_queue_length",
    "任务队列长度",
    ["queue_name"],
)
```

### 在 LLMClient 中使用

```python
async def complete(self, task_type: str, messages: list, **kwargs):
    model = await self.router.route(task_type)

    with llm_call_duration.labels(task_type=task_type, model=model.model_name).time():
        try:
            result = await self._call(model, messages, **kwargs)
            llm_call_total.labels(
                task_type=task_type, model=model.model_name, status="success"
            ).inc()
            llm_cost_total.labels(model=model.model_name).inc(result.cost_yuan)
            return result
        except Exception:
            llm_call_total.labels(
                task_type=task_type, model=model.model_name, status="failed"
            ).inc()
            raise
```

## 4. 告警规则

### 4.1 应用告警

| 规则名 | 条件 | 严重度 | 说明 |
|--------|------|--------|------|
| HighErrorRate | 5xx 比例 > 5%（5min） | critical | 服务错误率过高 |
| SlowRequests | P95 延迟 > 5s（5min） | warning | 请求延迟异常 |
| LLMCircuitOpen | `llm_circuit_open == 1` 持续 5min | critical | LLM 模型熔断 |
| LLMCostSpike | 1h 费用 > 日预算 20% | warning | 费用异常飙升 |
| QueueBacklog | 队列长度 > 100 持续 10min | warning | 任务积压 |

### 4.2 基础设施告警

| 规则名 | 条件 | 严重度 |
|--------|------|--------|
| HighCPU | CPU > 80%（5min） | warning |
| HighMemory | 内存 > 85%（5min） | warning |
| DiskAlmostFull | 磁盘 > 90% | critical |
| PGConnectionHigh | 连接数 > 最大值 80% | warning |
| RedisMemoryHigh | 内存 > maxmemory 80% | warning |

### 4.3 Prometheus 规则示例

```yaml
# prometheus/rules/app.yml
groups:
  - name: app-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "服务 {{ $labels.service }} 5xx 错误率 {{ $value | humanizePercentage }}"

      - alert: LLMCircuitOpen
        expr: llm_circuit_open == 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "模型 {{ $labels.model }} 熔断已触发"

      - alert: LLMCostSpike
        expr: |
          increase(llm_call_cost_yuan_total[1h]) > 
          (llm_cost_daily_budget * 0.2)
        labels:
          severity: warning
        annotations:
          summary: "1h 内 LLM 费用达日预算 {{ $value | humanize }}%"
```

## 5. 通知渠道

| 渠道 | 级别 | 配置 |
|------|------|------|
| 飞书机器人 | warning + critical | Webhook URL 配置在 AlertManager |
| 邮件 | critical | SMTP 配置 |
| 钉钉 | warning + critical | 备选渠道 |

### AlertManager 路由配置

```yaml
# alertmanager/config.yml
route:
  receiver: feishu-webhook
  group_by: [alertname, service]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    - match:
        severity: critical
      receiver: feishu-webhook
      repeat_interval: 1h

receivers:
  - name: feishu-webhook
    webhook_configs:
      - url: "http://alert-bridge:9095/feishu"
        send_resolved: true
```

## 6. Grafana 看板

### 预置看板

| 看板 | 内容 |
|------|------|
| **服务概览** | QPS、错误率、延迟（P50/P95/P99）、并发数 |
| **LLM 监控** | 调用量、费用趋势、成功率、延迟分布、熔断状态 |
| **基础设施** | CPU/内存/磁盘/网络、PG 连接数、Redis 状态 |
| **任务队列** | 队列长度、处理速度、失败率、重试次数 |

### 看板 JSON 管理

```
infra/grafana/dashboards/
├── service-overview.json
├── llm-monitoring.json
├── infrastructure.json
└── task-queue.json
```

以 Git 管理看板 JSON，通过 Grafana provisioning 自动加载。

## 7. MVP 部署拓扑

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./infra/prometheus:/etc/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.4.0
    volumes:
      - ./infra/grafana:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}

  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"

  postgres-exporter:
    image: quay.io/prometheuscommunity/postgres-exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}?sslmode=disable

  redis-exporter:
    image: oliver006/redis_exporter
    environment:
      - REDIS_ADDR=redis:6379
```
