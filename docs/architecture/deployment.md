# 部署架构

> 环境规划、容器编排、基础设施与运维策略

---

## 1. 环境规划

### 1.1 环境分层

| 环境 | 用途 | 基础设施 | 数据 |
|------|------|----------|------|
| **local** | 开发调试 | Docker Compose 单机 | SQLite / 本地 PG |
| **dev** | 联调测试 | 单节点云服务器 | 独立 PG + Redis |
| **staging** | 预发布验证 | 与生产同构（缩配） | 生产数据脱敏副本 |
| **production** | 线上运行 | K8s 集群 / 云托管 | 生产数据（多副本） |

### 1.2 首期简化方案（MVP）

首期无需完整 K8s，采用 **单机 Docker Compose** 部署：

```
┌─────────────────────────────────────────────────────────┐
│                    云服务器（4C8G+）                       │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Nginx       │  │ api-gateway  │  │ user-profile  │  │
│  │ (反向代理)   │──│ :8000        │  │ :8001         │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────┐  │
│  │content-engine│  │media-generation│  │ ai-tutor   │  │
│  │ :8002        │  │ :8003          │  │ :8004       │  │
│  └──────────────┘  └────────────────┘  └────────────┘  │
│                                                         │
│  ┌──────────────────────┐  ┌────────────┐              │
│  │learning-orchestrator │  │notification│              │
│  │ :8005                │  │ :8006      │              │
│  └──────────────────────┘  └────────────┘              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │PostgreSQL│  │  Redis   │  │  MinIO   │             │
│  │ :5432    │  │  :6379   │  │  :9000   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 容器化策略

### 2.1 镜像构建

每个服务独立 Dockerfile，统一采用多阶段构建：

```dockerfile
# 以 Python 服务为例（FastAPI）
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 镜像命名规范

```
registry.cn-hangzhou.aliyuncs.com/zhiqu/{service}:{env}-{git-sha7}

# 示例
zhiqu/api-gateway:dev-a1b2c3d
zhiqu/content-engine:prod-e4f5g6h
```

### 2.3 Docker Compose 编排（开发/MVP）

```yaml
# docker-compose.yml（核心结构）
version: "3.9"

x-common: &common
  restart: unless-stopped
  networks: [zhiqu-net]
  env_file: [.env]

services:
  # ─── 基础设施 ───
  postgres:
    image: pgvector/pgvector:pg16
    <<: *common
    ports: ["5432:5432"]
    volumes: [pg-data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: zhiqu
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    <<: *common
    ports: ["6379:6379"]
    command: redis-server --appendonly yes --maxmemory 512mb
    volumes: [redis-data:/data]

  minio:
    image: minio/minio:latest
    <<: *common
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    volumes: [minio-data:/data]
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}

  # ─── 应用服务 ───
  api-gateway:
    build: ./services/api-gateway
    <<: *common
    ports: ["8000:8000"]
    depends_on: [redis]

  user-profile:
    build: ./services/user-profile
    <<: *common
    ports: ["8001:8001"]
    depends_on: [postgres, redis]

  content-engine:
    build: ./services/content-engine
    <<: *common
    ports: ["8002:8002"]
    depends_on: [postgres, redis, minio]

  media-generation:
    build: ./services/media-generation
    <<: *common
    ports: ["8003:8003"]
    depends_on: [redis]

  ai-tutor:
    build: ./services/ai-tutor
    <<: *common
    ports: ["8004:8004"]
    depends_on: [postgres, redis]

  learning-orchestrator:
    build: ./services/learning-orchestrator
    <<: *common
    ports: ["8005:8005"]
    depends_on: [postgres, redis]

  notification:
    build: ./services/notification
    <<: *common
    ports: ["8006:8006"]
    depends_on: [redis]

  # ─── 反向代理 ───
  nginx:
    image: nginx:alpine
    <<: *common
    ports: ["80:80", "443:443"]
    volumes:
      - ./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./deploy/nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - api-gateway

volumes:
  pg-data:
  redis-data:
  minio-data:

networks:
  zhiqu-net:
    driver: bridge
```

---

## 3. 基础设施组件

### 3.1 数据库 — PostgreSQL 16 + pgvector

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| 版本 | pgvector/pgvector:pg16 | 云 RDS PG 16 + pgvector 插件 |
| 连接池 | 直连 | PgBouncer（transaction 模式） |
| 备份 | 无 | 每日自动备份，7天保留 |
| 读写分离 | 无 | 主从（analytics 走只读副本） |

**数据库拆分策略：**

MVP 阶段使用单库多 Schema：

```
zhiqu（database）
  ├── user_profile   — users, student_profiles, guardian_bindings
  ├── content        — textbooks, chapters, knowledge_points, kp_embeddings
  ├── media          — prompt_templates, generated_resources
  ├── learning       — tasks, task_assignments, learning_records
  ├── analytics      — daily_study_stats, weekly_reports
  ├── notification   — notification_templates, notification_logs
  └── conversation   — conversations, messages
```

后期如需拆分，每个 Schema 可独立迁移为独立数据库。

### 3.2 缓存 — Redis 7

| 用途 | Key 前缀 | TTL | 说明 |
|------|----------|-----|------|
| 短信验证码 | `sms:{phone}` | 5min | 登录验证 |
| JWT 黑名单 | `jwt:blacklist:{jti}` | Token剩余有效期 | 登出/强制下线 |
| 登录频率限制 | `rate:login:{phone}` | 1h | 滑动窗口 |
| 任务进度缓存 | `task:progress:{task_id}` | 30min | 热数据 |
| 用户信息缓存 | `user:{user_id}` | 10min | 高频查询 |

**Redis Streams 事件通道：**

```
stream:textbook.uploaded      → content-engine worker
stream:textbook.parsed        → media-generation worker
stream:resource.generated     → learning-orchestrator
stream:task.completed         → analytics-reporting
stream:report.ready           → notification
```

### 3.3 对象存储 — MinIO / OSS

| Bucket | 用途 | 访问策略 |
|--------|------|----------|
| `textbooks` | 教材原始文件 | 服务端私有 |
| `media-assets` | 生成的多媒体素材 | CDN 公开读 |
| `avatars` | 用户头像 | CDN 公开读 |
| `exports` | 导出报告 | 签名 URL（1h有效） |

### 3.4 LLM Gateway

统一管理所有 LLM 调用，不让业务服务直连模型提供商：

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│ content-engine  │────►│                  │────►│ OpenAI API    │
│ media-generation│────►│   LLM Gateway    │────►│ 智谱 API      │
│ ai-tutor        │────►│   (路由+限流+    │────►│ DeepSeek API  │
│ analytics       │────►│    缓存+降级)    │────►│ 本地模型       │
└─────────────────┘     └──────────────────┘     └───────────────┘
```

**核心能力：**
- **模型路由**：按任务类型选择最优模型（生成用大模型，嵌入用专用模型）
- **Token 限流**：按服务/用户配额限制
- **语义缓存**：相似 Query 命中缓存，降低成本
- **故障降级**：主模型不可用时自动切备用
- **用量统计**：按服务维度统计 Token 消耗与成本

MVP 阶段可简化为共享配置 + 直连，不单独部署 Gateway 进程。

---

## 4. 网络与安全

### 4.1 网络拓扑

```
                 Internet
                    │
              ┌─────┴─────┐
              │   CDN      │  ← 静态资源 + 前端
              │ (阿里云/CF) │
              └─────┬─────┘
                    │
              ┌─────┴─────┐
              │   Nginx    │  ← TLS 终止、限流、WAF
              │  :80/:443  │
              └─────┬─────┘
                    │
              ┌─────┴─────┐
              │api-gateway │  ← JWT 验证、路由
              │   :8000    │
              └─────┬─────┘
                    │
         ┌──── 内部网络（zhiqu-net）────┐
         │  服务间 HTTP 通信（内网）      │
         │  仅 api-gateway 对外暴露     │
         └───────────────────────────┘
```

### 4.2 安全策略

| 层面 | 措施 |
|------|------|
| **传输** | 全站 HTTPS（Let's Encrypt 自动续签） |
| **认证** | JWT（access: 2h, refresh: 7d），敏感操作二次验证 |
| **授权** | RBAC（admin / teacher / parent / student） |
| **API 限流** | Nginx + Redis 滑动窗口（全局 + 用户级） |
| **数据加密** | PG 敏感字段加密（手机号、身份证），Redis 密码保护 |
| **SQL 注入** | ORM 参数化查询，禁止拼接 SQL |
| **XSS/CSRF** | CSP Header，SameSite Cookie |
| **密钥管理** | `.env` 不入仓库，生产用云密钥管理（KMS） |
| **日志脱敏** | 手机号、Token 等敏感字段自动脱敏 |

### 4.3 CORS 配置

```python
# FastAPI CORS
origins = [
    "https://app.zhiqu.com",       # 学生端
    "https://admin.zhiqu.com",     # 管理后台
    "http://localhost:3000",       # 本地开发
]
```

---

## 5. CI/CD 流水线

### 5.1 流程概览

```
代码推送 ──► Lint + Type Check ──► 单元测试 ──► 构建镜像 ──► 推送仓库
                                                              │
                        ┌─────────────────────────────────────┘
                        │
                        ▼
              ┌──── dev 分支 ────┐    ┌── main 分支 ──┐
              │ 自动部署 → dev    │    │ 手动审批 →     │
              │ 环境               │    │ staging → prod │
              └───────────────────┘    └────────────────┘
```

### 5.2 分支策略

| 分支 | 用途 | 部署目标 |
|------|------|----------|
| `main` | 稳定主干 | staging → production（手动） |
| `dev` | 开发集成 | dev 环境（自动） |
| `feature/*` | 功能开发 | 仅 CI，不部署 |
| `hotfix/*` | 紧急修复 | staging → production（快速通道） |

### 5.3 GitHub Actions 示例

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: zhiqu_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install & Test
        run: |
          pip install -r requirements.txt
          pytest --cov --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v4

  build:
    needs: test
    if: github.ref == 'refs/heads/dev' || github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api-gateway, user-profile, content-engine, media-generation, ai-tutor, learning-orchestrator, notification]
    steps:
      - uses: actions/checkout@v4
      - name: Build & Push
        run: |
          docker build -t zhiqu/${{ matrix.service }}:${{ github.ref_name }}-${GITHUB_SHA::7} \
            ./services/${{ matrix.service }}
          docker push zhiqu/${{ matrix.service }}:${{ github.ref_name }}-${GITHUB_SHA::7}
```

---

## 6. 监控与可观测性

### 6.1 监控三支柱

| 支柱 | 工具 | 说明 |
|------|------|------|
| **Metrics** | Prometheus + Grafana | 请求延迟、错误率、资源使用 |
| **Logging** | Loki / ELK | 结构化日志（JSON），统一收集 |
| **Tracing** | OpenTelemetry + Jaeger | 请求链路追踪，跨服务调用关系 |

### 6.2 关键指标

**业务指标（Grafana Dashboard）：**

| 指标 | 阈值 | 告警 |
|------|------|------|
| API P99 延迟 | < 500ms | > 1s 触发告警 |
| API 错误率 | < 1% | > 5% 触发告警 |
| LLM 调用成功率 | > 95% | < 90% 触发降级 |
| LLM 平均响应时间 | < 10s | > 30s 告警 |
| 任务完成率 | 跟踪趋势 | 骤降 50% 告警 |
| 每日活跃用户 | 跟踪趋势 | - |

**基础设施指标：**

| 指标 | 正常范围 | 告警阈值 |
|------|----------|----------|
| CPU 使用率 | < 60% | > 85% |
| 内存使用率 | < 70% | > 85% |
| 磁盘使用率 | < 70% | > 85% |
| PG 连接数 | < 80% max | > 90% max |
| Redis 内存 | < 70% maxmemory | > 85% |

### 6.3 日志规范

统一 JSON 格式，方便结构化查询：

```json
{
  "timestamp": "2026-03-25T19:00:00Z",
  "level": "INFO",
  "service": "ai-tutor",
  "trace_id": "abc123def456",
  "user_id": "uuid-xxx",
  "method": "POST",
  "path": "/conversations/123/messages",
  "status": 200,
  "duration_ms": 2340,
  "message": "Message processed successfully"
}
```

### 6.4 告警通道

| 级别 | 触发条件 | 通知方式 |
|------|----------|----------|
| **P0 - 严重** | 服务不可用、数据丢失 | 电话 + 短信 + 飞书 |
| **P1 - 紧急** | 核心功能降级、高错误率 | 短信 + 飞书 |
| **P2 - 警告** | 性能下降、资源接近阈值 | 飞书群消息 |
| **P3 - 信息** | 异常趋势、非紧急事项 | 飞书机器人 |

---

## 7. 运维手册

### 7.1 常用操作

```bash
# 启动全部服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看指定服务日志
docker compose logs -f ai-tutor --tail=100

# 重启单个服务（不影响其他）
docker compose restart content-engine

# 数据库迁移
docker compose exec api-gateway alembic upgrade head

# 进入数据库
docker compose exec postgres psql -U zhiqu -d zhiqu

# Redis 检查
docker compose exec redis redis-cli info memory
docker compose exec redis redis-cli XLEN stream:task.completed
```

### 7.2 扩容策略

| 阶段 | 用户规模 | 部署方案 | 预估配置 |
|------|----------|----------|----------|
| **MVP** | < 500 | 单机 Docker Compose | 4C8G |
| **增长期** | 500 - 5000 | 单机升配 + 数据库外置 | 8C16G + 云 RDS |
| **规模期** | 5000 - 50000 | K8s 集群 + 服务拆分 | 多节点集群 |
| **成熟期** | > 50000 | 多可用区 + 弹性伸缩 | 按需动态调整 |

### 7.3 备份策略

| 数据 | 备份频率 | 保留时间 | 方式 |
|------|----------|----------|------|
| PostgreSQL | 每日全量 + 持续 WAL | 7天全量 + 30天WAL | pg_basebackup + WAL归档 |
| Redis AOF | 每日快照 | 3天 | BGSAVE + 文件拷贝 |
| MinIO 文件 | 跨区域同步 | 永久 | mc mirror |
| 配置文件 | Git 版本化 | 永久 | Git 仓库 |

### 7.4 灾难恢复

| 场景 | RTO | RPO | 恢复步骤 |
|------|-----|-----|----------|
| 单服务崩溃 | < 1min | 0 | Docker 自动重启（restart: unless-stopped） |
| 数据库故障 | < 30min | < 5min | WAL 恢复到最近一致点 |
| 整机故障 | < 2h | < 1h | 新机器 + 备份恢复 + 重新部署 |
| 数据误删 | < 4h | < 24h | 从备份恢复指定表/数据 |

---

## 8. 环境变量清单

```bash
# .env.example — 所有服务共享

# ─── 数据库 ───
DB_HOST=postgres
DB_PORT=5432
DB_USER=zhiqu
DB_PASSWORD=changeme
DB_NAME=zhiqu

# ─── Redis ───
REDIS_URL=redis://redis:6379/0

# ─── MinIO ───
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=changeme
MINIO_SECRET_KEY=changeme

# ─── LLM ───
LLM_PROVIDER=openai          # openai / zhipu / deepseek
LLM_API_KEY=sk-xxx
LLM_MODEL_CHAT=gpt-4o        # 对话模型
LLM_MODEL_EMBED=text-embedding-3-small  # 嵌入模型

# ─── SMS ───
SMS_PROVIDER=aliyun           # aliyun / tencent
SMS_ACCESS_KEY=xxx
SMS_SECRET_KEY=xxx
SMS_SIGN_NAME=知趣课堂
SMS_TEMPLATE_CODE=SMS_000001

# ─── 微信 ───
WX_APP_ID=wxXXX
WX_APP_SECRET=xxx

# ─── JWT ───
JWT_SECRET=changeme-with-random-string
JWT_ACCESS_TTL=7200           # 2 hours
JWT_REFRESH_TTL=604800        # 7 days

# ─── 应用 ───
APP_ENV=development           # development / staging / production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## 附：MVP 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/xxx/zhiqu-classroom.git
cd zhiqu-classroom

# 2. 初始化环境变量
cp .env.example .env
# 编辑 .env 填入实际值（至少 LLM_API_KEY）

# 3. 启动基础设施
docker compose up -d postgres redis minio

# 4. 数据库迁移
docker compose run --rm api-gateway alembic upgrade head

# 5. 启动全部服务
docker compose up -d

# 6. 健康检查
curl http://localhost:8000/health

# 7. 查看日志
docker compose logs -f
```