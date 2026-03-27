# LLM 调用专项日志

> 父文档：[README.md](./README.md)

---

## 1. LLM 日志流程

```
客户端请求 → LLM Router（路由决策日志）
           → LLM Client（调用日志）
           → Provider 响应
           → Token/Cost 计算
           → 结果日志（成功/失败/降级）
           → 异步入库（llm_call_logs 表）
```

## 2. 路由决策日志

```python
logger = structlog.get_logger("llm.routing")

# 正常路由
logger.info("LLM 路由决策",
    task_type="knowledge_extract",
    selected_provider="deepseek",
    selected_model="deepseek-v3",
    routing_rule_id="rule-uuid",
    candidates=["deepseek-v3", "qwen-2.5-72b"],
    reason="primary_available")

# 降级路由
logger.warning("LLM 路由降级",
    task_type="knowledge_extract",
    primary_provider="deepseek",
    primary_model="deepseek-v3",
    primary_status="circuit_open",
    fallback_provider="qwen",
    fallback_model="qwen-2.5-72b",
    reason="primary_circuit_breaker")
```

## 3. LLM 调用日志

```python
logger = structlog.get_logger("llm.call")

# 调用开始
logger.info("LLM 调用开始",
    task_type="knowledge_extract",
    provider="deepseek",
    model="deepseek-v3",
    temperature=0.7,
    max_tokens=4096,
    input_preview="请根据以下教材内容提取知识点..."[:100])

# 调用成功
logger.info("LLM 调用成功",
    task_type="knowledge_extract",
    provider="deepseek",
    model="deepseek-v3",
    input_tokens=1500,
    output_tokens=800,
    total_tokens=2300,
    cost_yuan=0.0023,
    llm_latency_ms=3200,
    is_fallback=False)

# 调用失败
logger.error("LLM 调用失败",
    task_type="knowledge_extract",
    provider="deepseek",
    model="deepseek-v3",
    error_type="timeout",
    llm_latency_ms=30000,
    retry_count=2,
    will_fallback=True,
    exc_info=True)
```

## 4. 熔断器日志

```python
logger = structlog.get_logger("llm.routing")

# 熔断触发
logger.error("LLM 熔断触发",
    provider="deepseek",
    model="deepseek-v3",
    failure_count=3,
    window_minutes=5,
    cooldown_minutes=10,
    affected_task_types=["knowledge_extract", "game_generate"])

# 熔断恢复
logger.info("LLM 熔断恢复",
    provider="deepseek",
    model="deepseek-v3",
    cooldown_elapsed_minutes=10,
    status="half_open")
```

## 5. 费用告警日志

```python
# 单次超限
logger.error("LLM 单次调用超费用上限",
    provider="openai",
    model="gpt-4o",
    estimated_cost=2.5,
    max_cost_per_call=1.0,
    task_type="quality_review",
    action="rejected")

# 日预算预警
logger.warning("LLM 日费用接近上限",
    date="2026-03-25",
    current_cost=85.5,
    daily_limit=100.0,
    usage_pct=85.5,
    top_consumers=[
        {"task_type": "knowledge_extract", "cost": 35.2},
        {"task_type": "game_generate", "cost": 28.1},
    ])
```

## 6. 入库流程

LLM 调用日志双写：

1. **实时输出**：structlog → stdout → Promtail → Loki（用于实时查询）
2. **异步入库**：调用完成后投递 Redis Stream → Consumer 写入 `llm_call_logs` 表（用于统计分析）

```python
# 入库前脱敏
from ..logging.sanitizer import sanitize_dict

log_entry = {
    "trace_id": trace_id,
    "task_type": "knowledge_extract",
    "provider_name": "deepseek",
    "model_name": "deepseek-v3",
    "input_messages": sanitize_dict(messages),  # 脱敏后存储
    "output_text": response.content[:2000],      # 截断
    "input_tokens": response.usage.input_tokens,
    "output_tokens": response.usage.output_tokens,
    "cost_yuan": calculated_cost,
    "latency_ms": latency,
    "status": "success",
}
await redis.xadd("stream:llm_call_logs", log_entry)
```
