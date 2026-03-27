# 基础设施配置 (infra)

> Docker Compose、Nginx、数据库迁移脚本等基础设施配置文件

## 目录结构

```
infra/
├── docker/
│   ├── docker-compose.yml       # 本地 / MVP 单机编排
│   ├── docker-compose.dev.yml   # 开发环境覆盖（热重载等）
│   ├── Dockerfile.api           # 后端服务镜像
│   ├── Dockerfile.app           # 学生端 H5 Nginx 镜像
│   └── Dockerfile.admin         # 管理后台 Nginx 镜像
├── nginx/
│   ├── nginx.conf               # 主配置
│   ├── conf.d/
│   │   ├── api.conf             # API 反代
│   │   ├── app.conf             # 学生端静态资源
│   │   └── admin.conf           # 管理后台静态资源
│   └── certs/                   # TLS 证书（.gitignore）
├── postgres/
│   ├── init.sql                 # 初始化脚本（创建 schema、扩展）
│   └── pg_hba.conf              # 访问控制（如需自定义）
├── redis/
│   └── redis.conf               # Redis 配置
├── minio/
│   └── init-buckets.sh          # 初始化 bucket 脚本
├── scripts/
│   ├── setup.sh                 # 一键初始化环境
│   └── backup.sh                # 备份脚本
└── README.md
```

## 快速启动

```bash
cd infra/docker

# 启动全部服务
docker compose up -d

# 仅启动基础设施（DB/Redis/MinIO）
docker compose up -d postgres redis minio

# 查看日志
docker compose logs -f api
```

## 核心服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| API Gateway | 8000 | 后端统一入口 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 + 消息队列 |
| MinIO | 9000 / 9001 | 对象存储 (API / Console) |
| Nginx | 80 / 443 | 反向代理 |

## 环境变量

复制 `.env.example` 到 `.env` 并填写：

```bash
cp .env.example .env
```

详见 [docs/architecture/deployment.md](../docs/architecture/deployment.md) 环境变量清单。

---

*最后更新：2026-03-25*
