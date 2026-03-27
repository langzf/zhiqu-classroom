# LLM 模型管理

> 父文档：[README.md](./README.md)

---

## 1. 概述

支持多 Provider 统一管理、运行时路由切换、模型级限速/降级/熔断。

```
管理后台 ──▶ model_providers ──▶ model_configs ──▶ model_routing_rules
                 │                     │                    │
                 ▼                     ▼                    ▼
          Provider 凭证         模型参数/限速        任务→模型映射
```

## 2. Provider 管理

### 数据模型

表 `model_providers`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| provider_name | VARCHAR(50) | 如 `deepseek`, `openai`, `qwen` |
| display_name | VARCHAR(100) | 展示名 |
| base_url | VARCHAR(500) | API 基础地址 |
| api_key_encrypted | TEXT | AES 加密存储 |
| status | VARCHAR(20) | `active` / `disabled` |
| config | JSONB | 额外配置（超时、重试次数等） |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 管理 API

```
GET    /api/v1/admin/llm/providers              🔑  列表
POST   /api/v1/admin/llm/providers              🔑  新增
PATCH  /api/v1/admin/llm/providers/:id           🔑  更新
DELETE /api/v1/admin/llm/providers/:id           🔑  删除（软删除）
```

## 3. 模型配置

### 数据模型

表 `model_configs`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| provider_id | UUID | 关联 provider（应用层校验） |
| model_name | VARCHAR(100) | 如 `deepseek-v3`, `gpt-4o` |
| display_name | VARCHAR(100) | |
| model_type | VARCHAR(50) | `chat` / `embedding` |
| status | VARCHAR(20) | `active` / `disabled` / `deprecated` |
| max_tokens | INT | 最大输出 token |
| default_temperature | NUMERIC(3,2) | 默认温度 |
| input_price_per_1k | NUMERIC(10,6) | 输入单价（元/千token） |
| output_price_per_1k | NUMERIC(10,6) | 输出单价 |
| max_cost_per_call | NUMERIC(10,4) | 单次调用费用上限 |
| rate_limit_rpm | INT | 每分钟请求上限 |
| rate_limit_tpm | INT | 每分钟 token 上限 |
| config | JSONB | 额外参数 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

唯一约束：`(provider_id, model_name)`

### 管理 API

```
GET    /api/v1/admin/llm/models                 🔑  列表（支持按 provider 筛选）
POST   /api/v1/admin/llm/models                 🔑  新增
PATCH  /api/v1/admin/llm/models/:id              🔑  更新配置
PATCH  /api/v1/admin/llm/models/:id/status       🔑  变更状态
```

## 4. 路由规则

### 数据模型

表 `model_routing_rules`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| task_type | VARCHAR(50) | 任务类型枚举 |
| primary_model_id | UUID | 主力模型 |
| fallback_model_id | UUID | 备选模型（nullable） |
| priority | INT | 优先级（数值小优先） |
| is_active | BOOLEAN | 是否启用 |
| conditions | JSONB | 附加条件（如年级范围、时间段） |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### task_type 枚举

| 值 | 说明 |
|----|------|
| `textbook_parse` | 教材解析 |
| `knowledge_extract` | 知识点抽取 |
| `game_generate` | 游戏化题目生成 |
| `video_script_generate` | 视频脚本生成 |
| `practice_generate` | 练习题生成 |
| `quality_review` | 内容质量审核 |
| `report_generate` | 学习报告生成 |
| `embedding` | 文本向量化 |

### 管理 API

```
GET    /api/v1/admin/llm/routing-rules           🔑  列表
POST   /api/v1/admin/llm/routing-rules           🔑  新增
PATCH  /api/v1/admin/llm/routing-rules/:id        🔑  更新
```

## 5. 路由决策流程

```python
async def route(task_type: str, **context) -> ModelConfig:
    # 1. 查找该 task_type 的活跃路由规则（按 priority 排序）
    rules = await get_active_rules(task_type)

    for rule in rules:
        # 2. 检查主力模型状态
        primary = await get_model(rule.primary_model_id)
        if primary.status == "active" and not is_circuit_open(primary):
            if check_rate_limit(primary):
                return primary

        # 3. 主力不可用，尝试备选
        if rule.fallback_model_id:
            fallback = await get_model(rule.fallback_model_id)
            if fallback.status == "active" and not is_circuit_open(fallback):
                logger.warning("LLM 路由降级", ...)
                return fallback

    raise NoAvailableModelError(task_type)
```

## 6. 熔断策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 失败窗口 | 5 分钟 | 统计窗口 |
| 失败阈值 | 3 次 | 窗口内失败次数 |
| 熔断时长 | 10 分钟 | 熔断后冷却时间 |
| 半开探测 | 1 次/分钟 | 冷却后探测是否恢复 |

```python
# 基于 Redis 实现
class CircuitBreaker:
    async def record_failure(self, model_id: str):
        key = f"circuit:{model_id}:failures"
        count = await redis.incr(key)
        await redis.expire(key, 300)  # 5分钟窗口
        if count >= 3:
            await redis.setex(f"circuit:{model_id}:open", 600, "1")
            logger.error("LLM 熔断触发", model_id=model_id, failure_count=count)

    async def is_open(self, model_id: str) -> bool:
        return bool(await redis.get(f"circuit:{model_id}:open"))

    async def record_success(self, model_id: str):
        await redis.delete(f"circuit:{model_id}:failures")
        await redis.delete(f"circuit:{model_id}:open")
```

## 7. 费用控制

| 机制 | 说明 |
|------|------|
| **单次上限** | `max_cost_per_call` 字段，预估超限则拒绝 |
| **日预算** | `llm_usage_daily` 聚合，接近阈值告警 |
| **月预算** | 配置在 `sys_configs`，超限自动降级到低价模型 |

预估费用计算：

```python
def estimate_cost(model: ModelConfig, input_tokens: int, max_output_tokens: int) -> float:
    input_cost = (input_tokens / 1000) * model.input_price_per_1k
    output_cost = (max_output_tokens / 1000) * model.output_price_per_1k
    return input_cost + output_cost
```
