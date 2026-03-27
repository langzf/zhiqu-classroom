# 日志采集架构

> 父文档：[README.md](./README.md)

---

## 1. 架构概览

```
┌──────────────┐   stdout/JSON    ┌──────────┐   push    ┌──────┐   query   ┌─────────┐
│ FastAPI 服务 │ ───────────────▶ │ Promtail │ ───────▶ │ Loki │ ◀──────── │ Grafana │
│ (structlog)  │                  │          │          │      │           │         │
└──────────────┘                  └──────────┘          └──────┘           └─────────┘
       │                                                   │
       │  异步入库                                         │  LogQL
       ▼                                                   ▼
 ┌───────────┐                                      ┌───────────┐
 │ Redis     │ ─── Consumer ──▶ PostgreSQL          │ Dashboard │
 │ Stream    │    (llm_call_logs / audit_logs)       │ + Alert   │
 └───────────┘                                      └───────────┘
```

## 2. 各组件职责

| 组件 | 版本 | 职责 |
|------|------|------|
| **structlog** | 最新 | 结构化日志生成，JSON 序列化 |
| **Docker log driver** | json-file | 捕获容器 stdout |
| **Promtail** | 3.x | 日志采集、label 提取、推送 Loki |
| **Loki** | 3.x | 日志存储、索引、查询 |
| **Grafana** | 11.x | 可视化、告警 |

## 3. MVP 简化方案

首期不需要复杂的采集管道：

```
单机版：
  Docker Compose
    └── services → stdout → Docker json-file log driver
    └── promtail → 读取 /var/lib/docker/containers/*/*.log
    └── loki → 本地存储
    └── grafana → :3000

最简版（开发/测试）：
  service stdout → 终端查看
  无需 Promtail/Loki
```

## 4. Promtail 配置

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      # 从容器 label 提取服务名
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        target_label: 'service'
    pipeline_stages:
      # 解析 Docker JSON log wrapper
      - docker: {}
      # 解析 structlog JSON
      - json:
          expressions:
            level: level
            logger: logger
            trace_id: trace_id
            user_id: user_id
            message: message
            duration_ms: duration_ms
      - labels:
          level:
          service:
      # 可选：丢弃 DEBUG（生产环境减少存储）
      # - match:
      #     selector: '{level="DEBUG"}'
      #     action: drop
```

## 5. Loki 配置

```yaml
# loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2026-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 720h   # 30天
  max_query_length: 721h

compactor:
  working_directory: /loki/retention
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
```

## 6. Docker Compose 片段

```yaml
# docker-compose.logging.yml
services:
  loki:
    image: grafana/loki:3.3.0
    ports:
      - "3100:3100"
    volumes:
      - ./config/loki-config.yml:/etc/loki/config.yaml
      - loki-data:/loki
    command: -config.file=/etc/loki/config.yaml

  promtail:
    image: grafana/promtail:3.3.0
    volumes:
      - ./config/promtail-config.yml:/etc/promtail/config.yaml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command: -config.file=/etc/promtail/config.yaml

  grafana:
    image: grafana/grafana:11.5.0
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  loki-data:
  grafana-data:
```
