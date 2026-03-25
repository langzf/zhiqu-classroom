# 配置中心

> 父文档：[README.md](./README.md)

---

## 1. 概述

统一管理应用运行时配置，支持分层覆盖、热更新。MVP 阶段使用数据库表 + Redis 缓存，后续可迁移至 Nacos/Consul。

```
sys_configs（DB 持久化）
       │  启动加载 + 变更同步
       ▼
  Redis 缓存（热读取）
       │
       ▼
  ConfigService.get(key)
```

## 2. 数据模型

表 `sys_configs`：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| config_key | VARCHAR(200) | NOT NULL, UNIQUE | 配置键，点分命名 |
| config_value | TEXT | NOT NULL | 配置值（字符串形式） |
| value_type | VARCHAR(20) | NOT NULL, DEFAULT 'string' | `string` / `int` / `float` / `bool` / `json` |
| category | VARCHAR(50) | NOT NULL | 分类：`system` / `llm` / `notification` / `business` |
| description | VARCHAR(500) | NULL | 说明 |
| is_sensitive | BOOLEAN | NOT NULL, DEFAULT false | 敏感值是否加密存储 |
| is_readonly | BOOLEAN | NOT NULL, DEFAULT false | 是否禁止运行时修改 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

### 索引

| 索引名 | 字段 | 说明 |
|--------|------|------|
| `uniq_sys_configs_key` | config_key | 唯一索引（已含在 UNIQUE 约束中） |
| `idx_sys_configs_category` | category | 按分类查询 |

## 3. 分层策略

配置优先级从高到低：

```
环境变量（ENV）         ← 最高优先级，运维/部署层面
  ↓
sys_configs 表值        ← 运行时可调，管理后台修改
  ↓
代码默认值（DEFAULT）    ← 兜底，硬编码在配置类中
```

### 配置类示例

```python
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM 相关配置 — 环境变量 > 数据库 > 默认值"""

    cost_daily_warn: float = 100.0
    cost_daily_limit: float = 200.0
    cost_monthly_warn: float = 2000.0
    cost_monthly_limit: float = 5000.0

    class Config:
        env_prefix = "LLM_"
```

## 4. 配置服务

```python
class ConfigService:
    """统一配置读取，带 Redis 缓存"""

    CACHE_PREFIX = "config:"
    CACHE_TTL = 300  # 5 分钟

    async def get(self, key: str, default=None):
        """读取配置：Redis 缓存 → DB → 默认值"""
        # 1. 环境变量优先
        env_key = key.upper().replace(".", "_")
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return self._cast(env_val, key)

        # 2. Redis 缓存
        cached = await self.redis.get(f"{self.CACHE_PREFIX}{key}")
        if cached is not None:
            return self._deserialize(cached)

        # 3. 数据库
        config = await self.repo.get_by_key(key)
        if config:
            value = self._cast(config.config_value, config.value_type)
            await self.redis.setex(
                f"{self.CACHE_PREFIX}{key}", self.CACHE_TTL, self._serialize(value)
            )
            return value

        return default

    async def set(self, key: str, value, operator: str = "system"):
        """更新配置值（写穿 DB + 清除缓存）"""
        await self.repo.upsert(key, str(value))
        await self.redis.delete(f"{self.CACHE_PREFIX}{key}")
        logger.info("配置更新", config_key=key, operator=operator)

    async def refresh_cache(self):
        """批量刷新缓存（启动时 / 手动触发）"""
        configs = await self.repo.list_all()
        pipe = self.redis.pipeline()
        for c in configs:
            pipe.setex(
                f"{self.CACHE_PREFIX}{c.config_key}",
                self.CACHE_TTL,
                self._serialize(self._cast(c.config_value, c.value_type)),
            )
        await pipe.execute()
```

## 5. 预置配置项

| 配置键 | 默认值 | 类型 | 分类 | 说明 |
|--------|--------|------|------|------|
| `llm.cost.daily_warn` | 100 | float | llm | 日费用预警阈值（元） |
| `llm.cost.daily_limit` | 200 | float | llm | 日费用硬限（元） |
| `llm.cost.monthly_warn` | 2000 | float | llm | 月费用预警阈值（元） |
| `llm.cost.monthly_limit` | 5000 | float | llm | 月费用硬限（元） |
| `system.maintenance_mode` | false | bool | system | 维护模式开关 |
| `system.register_enabled` | true | bool | system | 是否开放注册 |
| `notification.channels` | `["feishu"]` | json | notification | 告警通知渠道 |
| `business.max_students_per_class` | 60 | int | business | 班级最大学生数 |
| `business.default_task_duration_min` | 30 | int | business | 默认任务时长（分钟） |

## 6. 管理 API

```
GET    /api/v1/admin/configs                    🔑  配置列表（支持按 category 筛选）
GET    /api/v1/admin/configs/:key               🔑  查询单个配置
PUT    /api/v1/admin/configs/:key               🔑  更新配置值
POST   /api/v1/admin/configs/refresh            🔑  手动刷新缓存
```

## 7. 变更审计

每次配置变更自动写入审计日志（参见 [audit.md](./audit.md)）：

```python
await audit_service.log(
    action="config.update",
    resource_type="sys_config",
    resource_id=config.id,
    operator_id=current_user.id,
    changes={"key": key, "old_value": old, "new_value": new},
)
```
