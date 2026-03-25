# 平台支撑系统设计（v1.0）

> 适用范围：zhiqu-classroom MVP 阶段
> 本文档定义 LLM 模型管理、统一日志规范、配置管理、健康检查、监控告警等辅助支撑系统。

---

## 目录

1. [LLM 模型管理](#1-llm-模型管理)
2. [LLM 调用历史与用量统计](#2-llm-调用历史与用量统计)
3. [统一日志规范](#3-统一日志规范)
4. [配置管理](#4-配置管理)
5. [健康检查与优雅停机](#5-健康检查与优雅停机)
6. [监控告警](#6-监控告警)
7. [审计日志](#7-审计日志)
8. [异步任务与重试](#8-异步任务与重试)
9. [安全基线](#9-安全基线)

---

## 1. LLM 模型管理

### 1.1 设计目标

- 支持多模型 provider（DeepSeek、Qwen、OpenAI、Claude）统一管理
- 运行时可切换模型、调整参数，无需重新部署
- 支持模型级别的限速、降级、熔断
- 管理后台可视化配置

### 1.2 核心概念

```
┌─────────────────────────────────────────────┐
│              model_providers                 │
│  (DeepSeek / Qwen / OpenAI / Claude ...)    │
│  ├── api_base_url                           │
│  ├── api_key (加密存储)                      │
│  ├── rate_limit                             │
│  └── status (active / disabled)             │
└──────────────────┬──────────────────────────┘
                   │ 1:N
                   ▼
┌─────────────────────────────────────────────┐
│              model_configs                   │
│  (deepseek-v3 / qwen-2.5-72b / gpt-4o)    │
│  ├── provider_id                            │
│  ├── model_name                             │
│  ├── display_name                           │
│  ├── default_params (temp, top_p, max_tok)  │
│  ├── cost_per_1k_input / output             │
│  ├── priority (路由优先级)                   │
│  ├── supported_tasks []                     │
│  └── status                                 │
└──────────────────┬──────────────────────────┘
                   │ N:N
                   ▼
┌─────────────────────────────────────────────┐
│              model_routing_rules             │
│  按 task_type 路由到不同模型                  │
│  ├── task_type (知识点抽取/内容生成/质量评估)  │
│  ├── primary_model_id                       │
│  ├── fallback_model_id                      │
│  └── constraints (max_cost, max_latency)    │
└─────────────────────────────────────────────┘
```

### 1.3 数据模型

#### model_providers（模型供应商）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| name | VARCHAR(50) | NOT NULL, UNIQUE | 供应商标识：`deepseek`, `openai`, `anthropic`, `qwen` |
| display_name | VARCHAR(100) | NOT NULL | 显示名称 |
| api_base_url | VARCHAR(500) | NOT NULL | API 基础地址 |
| api_key_encrypted | TEXT | NOT NULL | 加密存储的 API Key |
| rate_limit_rpm | INT | NULL | 每分钟请求限制 |
| rate_limit_tpm | INT | NULL | 每分钟 Token 限制 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | `active` / `disabled` |
| health_check_url | VARCHAR(500) | NULL | 健康检查端点 |
| last_health_at | TIMESTAMP | NULL | 最后健康检查时间 |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### model_configs（模型配置）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| provider_id | UUID | FK → model_providers.id, NOT NULL | |
| model_name | VARCHAR(100) | NOT NULL | API 调用用的模型名，如 `deepseek-chat` |
| display_name | VARCHAR(100) | NOT NULL | 管理后台显示名 |
| description | TEXT | NULL | 模型说明 |
| default_params | JSONB | NOT NULL | 默认调用参数 |
| cost_per_1k_input | DECIMAL(10,6) | NOT NULL, DEFAULT 0 | 每千 input token 费用（元） |
| cost_per_1k_output | DECIMAL(10,6) | NOT NULL, DEFAULT 0 | 每千 output token 费用（元） |
| max_context_tokens | INT | NOT NULL | 最大上下文长度 |
| supported_tasks | JSONB | NOT NULL, DEFAULT '[]' | 支持的任务类型列表 |
| priority | INT | NOT NULL, DEFAULT 0 | 路由优先级（越大越优先） |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | `active` / `disabled` / `deprecated` |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**default_params 示例：**
```json
{
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 4096,
  "presence_penalty": 0,
  "frequency_penalty": 0
}
```

**UNIQUE 约束：** `(provider_id, model_name)`

#### model_routing_rules（模型路由规则）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_type | VARCHAR(50) | NOT NULL, UNIQUE | 任务类型 |
| description | VARCHAR(200) | NULL | 规则说明 |
| primary_model_id | UUID | FK → model_configs.id, NOT NULL | 主力模型 |
| fallback_model_id | UUID | FK → model_configs.id, NULL | 降级模型 |
| max_cost_per_call | DECIMAL(10,4) | NULL | 单次调用费用上限（元） |
| max_latency_ms | INT | NULL | 最大允许延迟（毫秒） |
| retry_count | INT | NOT NULL, DEFAULT 2 | 重试次数 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**task_type 枚举：**

| 值 | 说明 |
|----|------|
| `textbook_parse` | 教材解析与结构化 |
| `knowledge_extract` | 知识点抽取 |
| `game_generate` | 游戏内容生成 |
| `video_script_generate` | 视频脚本生成 |
| `practice_generate` | 练习题生成 |
| `quality_review` | 质量评估 |
| `report_generate` | 学习报告生成 |
| `embedding` | 文本向量化 |

### 1.4 LLM 客户端封装

```python
# services/shared/llm/client.py 伪代码

class LLMClient:
    """统一 LLM 调用入口"""
    
    async def complete(
        self,
        task_type: str,           # 路由到对应模型
        messages: list[Message],
        *,
        params_override: dict | None = None,  # 覆盖默认参数
        trace_id: str | None = None,
        user_id: str | None = None,
        metadata: dict | None = None,
    ) -> LLMResponse:
        """
        流程：
        1. 查路由规则 → 拿到 primary model
        2. 合并 default_params + params_override
        3. 检查限速
        4. 调用 provider API
        5. 失败 → 重试 → 降级到 fallback model
        6. 记录调用日志 (llm_call_logs)
        7. 返回结构化响应
        """
        ...
    
    async def stream(
        self,
        task_type: str,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[LLMChunk]:
        """流式输出"""
        ...
```

### 1.5 熔断与降级策略

| 场景 | 策略 |
|------|------|
| 单次调用超时 | 超过 `max_latency_ms` 取消请求，切 fallback |
| 连续失败 | 5 分钟内 3 次失败 → 该模型熔断 10 分钟 |
| 费用超限 | 单次超 `max_cost_per_call` → 拒绝并告警 |
| provider 不可用 | 自动切 fallback，通知管理员 |
| 全部不可用 | 返回服务降级提示，记录告警 |

---

## 2. LLM 调用历史与用量统计

### 2.1 调用日志表

#### llm_call_logs（LLM 调用记录）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| trace_id | VARCHAR(64) | NOT NULL | 请求链路 ID |
| task_type | VARCHAR(50) | NOT NULL | 业务任务类型 |
| model_config_id | UUID | NOT NULL | 使用的模型配置 |
| provider_name | VARCHAR(50) | NOT NULL | 冗余：供应商名称 |
| model_name | VARCHAR(100) | NOT NULL | 冗余：模型名称 |
| caller_service | VARCHAR(50) | NOT NULL | 调用方服务名 |
| user_id | UUID | NULL | 触发调用的用户（如有） |
| input_messages | JSONB | NOT NULL | 输入 messages（脱敏后） |
| input_tokens | INT | NOT NULL | 输入 token 数 |
| output_content | TEXT | NOT NULL | 输出内容 |
| output_tokens | INT | NOT NULL | 输出 token 数 |
| total_tokens | INT | NOT NULL | 总 token 数 |
| cost_yuan | DECIMAL(10,6) | NOT NULL | 本次调用费用（元） |
| latency_ms | INT | NOT NULL | 响应延迟（毫秒） |
| status | VARCHAR(20) | NOT NULL | `success` / `failed` / `timeout` / `fallback` |
| error_message | TEXT | NULL | 失败时的错误信息 |
| params_used | JSONB | NOT NULL | 实际使用的调用参数 |
| is_fallback | BOOLEAN | NOT NULL, DEFAULT false | 是否使用了降级模型 |
| metadata | JSONB | DEFAULT '{}' | 扩展信息（关联的 resource_id 等） |
| created_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_lcl_trace` ON (trace_id)
- `idx_lcl_task_type` ON (task_type)
- `idx_lcl_model` ON (model_config_id)
- `idx_lcl_user` ON (user_id)
- `idx_lcl_status` ON (status)
- `idx_lcl_created` ON (created_at)
- `idx_lcl_caller` ON (caller_service, created_at)

**分区策略：** 按 `created_at` 月份范围分区，保留 6 个月热数据，冷数据归档到对象存储。

### 2.2 用量统计表

#### llm_usage_daily（每日 LLM 用量汇总）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| stat_date | DATE | NOT NULL | 统计日期 |
| provider_name | VARCHAR(50) | NOT NULL | |
| model_name | VARCHAR(100) | NOT NULL | |
| task_type | VARCHAR(50) | NOT NULL | |
| total_calls | INT | NOT NULL, DEFAULT 0 | 调用次数 |
| success_calls | INT | NOT NULL, DEFAULT 0 | 成功次数 |
| failed_calls | INT | NOT NULL, DEFAULT 0 | 失败次数 |
| fallback_calls | INT | NOT NULL, DEFAULT 0 | 降级次数 |
| total_input_tokens | BIGINT | NOT NULL, DEFAULT 0 | 总输入 tokens |
| total_output_tokens | BIGINT | NOT NULL, DEFAULT 0 | 总输出 tokens |
| total_cost_yuan | DECIMAL(12,4) | NOT NULL, DEFAULT 0 | 总费用（元） |
| avg_latency_ms | INT | NOT NULL, DEFAULT 0 | 平均延迟 |
| p95_latency_ms | INT | NOT NULL, DEFAULT 0 | P95 延迟 |
| p99_latency_ms | INT | NOT NULL, DEFAULT 0 | P99 延迟 |
| created_at | TIMESTAMP | NOT NULL | |

**UNIQUE 约束：** `(stat_date, provider_name, model_name, task_type)`

### 2.3 管理后台功能

管理后台 → LLM 管理模块：

| 页面 | 功能 |
|------|------|
| **供应商管理** | 增删改查 provider，API Key 管理（密文展示），健康状态 |
| **模型管理** | 模型列表，参数配置，启用/停用，标记废弃 |
| **路由配置** | 按任务类型配置主力/降级模型，费用和延迟约束 |
| **调用日志** | 分页查看调用记录，按时间/模型/任务类型/状态筛选，详情查看输入输出 |
| **用量看板** | 日/周/月维度：调用量趋势、费用分布、成功率、延迟分布 |
| **费用预警** | 日/月费用阈值设置，超限告警 |

### 2.4 管理接口

```
GET    /api/v1/admin/llm/providers                 🔑  供应商列表
POST   /api/v1/admin/llm/providers                 🔑  创建供应商
PATCH  /api/v1/admin/llm/providers/:id             🔑  更新供应商
DELETE /api/v1/admin/llm/providers/:id             🔑  删除供应商

GET    /api/v1/admin/llm/models                    🔑  模型列表
POST   /api/v1/admin/llm/models                    🔑  创建模型配置
PATCH  /api/v1/admin/llm/models/:id                🔑  更新模型配置
PATCH  /api/v1/admin/llm/models/:id/status         🔑  启用/停用模型

GET    /api/v1/admin/llm/routing-rules             🔑  路由规则列表
POST   /api/v1/admin/llm/routing-rules             🔑  创建路由规则
PATCH  /api/v1/admin/llm/routing-rules/:id         🔑  更新路由规则

GET    /api/v1/admin/llm/call-logs                 🔑  调用日志列表（分页）
GET    /api/v1/admin/llm/call-logs/:id             🔑  调用日志详情

GET    /api/v1/admin/llm/usage/daily               🔑  每日用量统计
GET    /api/v1/admin/llm/usage/summary             🔑  用量汇总看板数据
```

---

## 3. 统一日志规范

### 3.1 设计目标

- **全局统一**：所有服务、所有模块使用同一日志格式和接口
- **结构化输出**：JSON 格式，便于 Loki / ELK 集中查询
- **链路贯通**：通过 trace_id + span_id 串联完整请求链路
- **分级规范**：明确各级别使用场景，避免滥用
- **零侵入接入**：通过中间件和装饰器自动注入上下文，业务代码最小改动
- **敏感脱敏**：手机号、身份证号、API Key 等自动脱敏

### 3.2 日志级别规范

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 开发调试信息，生产环境默认关闭 | 变量值、SQL 语句、中间计算结果 |
| **INFO** | 正常业务流程关键节点 | 用户登录成功、任务创建、LLM 调用完成 |
| **WARNING** | 异常但可自动恢复 | 重试成功、缓存未命中、LLM 降级到 fallback |
| **ERROR** | 业务异常，需关注但服务仍可用 | 第三方调用失败、参数校验失败、数据不一致 |
| **CRITICAL** | 服务不可用级别的严重错误 | 数据库连接断开、所有 LLM provider 不可用 |

**强制规则：**
- ❌ 禁止用 `print()` 输出日志
- ❌ 禁止在 INFO 级别打印大量循环日志
- ❌ 禁止在日志中输出完整 API Key、密码、Token
- ✅ 每个请求至少一条 INFO（入口 + 出口）
- ✅ 所有异常必须记录 ERROR 并附 traceback

### 3.3 日志格式（JSON 结构化）

```json
{
  "timestamp": "2026-03-25T14:23:45.123+08:00",
  "level": "INFO",
  "logger": "content_engine.textbook_parser",
  "message": "教材解析完成",
  "service": "content-engine",
  "instance": "content-engine-7d8f9b-abc12",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "span_id": "1234abcd",
  "parent_span_id": "5678efgh",
  "user_id": "550e8400-...",
  "request_id": "req-xxxx",
  "duration_ms": 1523,
  "data": {
    "textbook_id": "...",
    "chapter_count": 12,
    "knowledge_points": 48
  },
  "error": null
}
```

**固定字段说明：**

| 字段 | 来源 | 说明 |
|------|------|------|
| timestamp | 自动 | ISO 8601 带时区 |
| level | 代码指定 | 日志级别 |
| logger | 自动 | Python logger name（模块路径） |
| message | 代码指定 | 人类可读描述 |
| service | 环境变量 | 服务名，`SERVICE_NAME` |
| instance | 自动 | Pod name / hostname |
| trace_id | 中间件 | 请求链路 ID（来自 `X-Request-ID` 或自动生成） |
| span_id | 中间件 | 当前操作 span |
| parent_span_id | 中间件 | 父 span（跨服务调用时） |
| user_id | 中间件 | 当前认证用户（从 JWT 解析） |
| request_id | 中间件 | 客户端传入的 `X-Request-ID` |
| duration_ms | 代码/中间件 | 操作耗时 |
| data | 代码指定 | 业务数据（结构化 KV） |
| error | 自动 | 异常信息 + traceback |

### 3.4 日志基础设施（structlog）

```python
# services/shared/logging/config.py

import structlog
import logging
import sys
import os
import socket
from contextvars import ContextVar

# ── 上下文变量（中间件注入，自动附加到每条日志）──
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def _add_service_context(logger, method_name, event_dict):
    """注入 service + instance"""
    event_dict["service"] = os.getenv("SERVICE_NAME", "unknown")
    event_dict["instance"] = os.getenv("HOSTNAME", socket.gethostname())
    return event_dict


def _add_trace_context(logger, method_name, event_dict):
    """注入链路上下文"""
    event_dict.setdefault("trace_id", trace_id_var.get(""))
    event_dict.setdefault("span_id", span_id_var.get(""))
    event_dict.setdefault("user_id", user_id_var.get(""))
    event_dict.setdefault("request_id", request_id_var.get(""))
    return event_dict


def _sanitize_sensitive(logger, method_name, event_dict):
    """敏感字段脱敏"""
    from .sanitizer import sanitize_dict
    return sanitize_dict(event_dict)


def setup_logging(
    service_name: str,
    level: str = "INFO",
    json_output: bool = True,
):
    """初始化日志系统——每个服务启动时调用一次"""
    os.environ.setdefault("SERVICE_NAME", service_name)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        _add_service_context,
        _add_trace_context,
        _sanitize_sensitive,
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(
            structlog.processors.JSONRenderer(ensure_ascii=False)
        )
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


def get_logger(name: str):
    """获取 logger"""
    return structlog.get_logger(name)
```

### 3.5 敏感字段脱敏

```python
# services/shared/logging/sanitizer.py

import re
import copy

SENSITIVE_KEYS = {"password", "secret", "api_key", "token", "authorization"}

PHONE_RE = re.compile(r'1[3-9]\d{9}')
KEY_RE = re.compile(r'(sk-|ak-|Bearer\s+)\S{8,}')

def sanitize_value(val: str) -> str:
    val = PHONE_RE.sub(lambda m: m.group()[:3] + '****' + m.group()[-4:], val)
    val = KEY_RE.sub(lambda m: m.group()[:6] + '****' + m.group()[-4:], val)
    return val

def sanitize_dict(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        if k.lower() in SENSITIVE_KEYS:
            result[k] = "***"
        elif isinstance(v, str):
            result[k] = sanitize_value(v)
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v)
        else:
            result[k] = v
    return result
```

### 3.6 FastAPI 请求日志中间件

```python
# services/shared/logging/middleware.py

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_logger, trace_id_var, span_id_var, user_id_var, request_id_var


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """自动记录请求出入口日志 + 注入链路上下文"""

    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        span_id = uuid.uuid4().hex[:8]

        trace_id_var.set(trace_id)
        span_id_var.set(span_id)
        request_id_var.set(trace_id)
        user_id_var.set(getattr(request.state, "user_id", ""))

        logger = get_logger("http.access")
        logger.info(
            "请求开始",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "",
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.error("请求异常", method=request.method, path=request.url.path, exc_info=True)
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "请求完成",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Trace-ID"] = trace_id
        return response
```

### 3.7 业务日志示例（规范 vs 反面）

```python
logger = get_logger("content_engine.textbook_parser")

# ✅ 正确 — 关键节点 INFO，附带结构化数据
logger.info("开始解析教材", textbook_id=tid, file_type="pdf")
logger.info("教材解析完成", textbook_id=tid, chapters=12, duration_ms=1523)

# ✅ 正确 — 降级用 WARNING
logger.warning("LLM 调用降级", primary="deepseek-v3", fallback="qwen-2.5-72b")

# ✅ 正确 — 异常用 ERROR + exc_info
try:
    result = await llm.complete(...)
except Exception as e:
    logger.error("LLM 调用失败", task_type="knowledge_extract", exc_info=True)
    raise

# ❌ 错误 — 禁止 print
print(f"processing {item}")

# ❌ 错误 — 禁止明文密钥
logger.info("calling api", api_key=key)

# ❌ 错误 — 禁止循环中高频 INFO
for item in items:
    logger.info("processed", item_id=item.id)  # 改用 DEBUG 或循环外汇总
```

### 3.8 日志采集管道（MVP 阶段）

```
┌──────────┐  stdout/JSON   ┌───────────┐  push   ┌───────┐
│  Service  │ ─────────────► │  Promtail │ ──────► │ Loki  │
│ (structlog)│               │ (sidecar) │         │       │
└──────────┘                └───────────┘         └──┬────┘
                                                     │ query
                                                     ▼
                                                ┌──────────┐
                                                │ Grafana  │
                                                │ 日志面板  │
                                                └──────────┘
```

MVP 简化：服务 JSON → stdout → Docker log driver → Loki → Grafana Explore。

### 3.9 日志查询示例（LogQL）

```logql
# 查某个 trace 的完整链路
{service="content-engine"} | json | trace_id="a1b2c3d4-..."

# 查某服务所有错误
{service="media-generation"} | json | level="ERROR"

# 查 LLM 调用超时
{service=~".+"} | json | message="LLM 调用失败" | error=~".*timeout.*"

# 查某用户的操作轨迹
{service=~".+"} | json | user_id="550e8400-..."

# 查慢请求 (>3s)
{service=~".+"} | json | duration_ms > 3000
```

---

## 4. 配置管理

### 4.1 设计原则

| 原则 | 说明 |
|------|------|
| 分层覆盖 | 默认值 → 配置文件 → 环境变量 → 远程配置中心（优先级递增） |
| 敏感分离 | 密钥、凭证等敏感配置不入代码仓库，通过环境变量或密钥管理注入 |
| 环境隔离 | dev / staging / prod 各自独立配置，通过 `APP_ENV` 区分 |
| 热更新友好 | 非关键配置支持运行时重载，无需重启服务 |

### 4.2 配置结构

```
config/
├── base.yaml          # 所有环境共享的默认值
├── dev.yaml           # 开发环境覆盖
├── staging.yaml       # 预发布环境覆盖
├── prod.yaml          # 生产环境覆盖
└── .env.example       # 环境变量模板（不含真实值）
```

### 4.3 Pydantic Settings 实现

```python
# services/shared/config/settings.py

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    name: str = "zhiqu_classroom"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    model_config = {"env_prefix": "DB_"}


class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    model_config = {"env_prefix": "REDIS_"}


class LLMSettings(BaseSettings):
    default_provider: str = "deepseek"
    default_model: str = "deepseek-v3"
    request_timeout: int = 60
    max_retries: int = 3
    circuit_breaker_threshold: int = 3
    circuit_breaker_window: int = 300       # 秒
    circuit_breaker_recovery: int = 600     # 秒

    model_config = {"env_prefix": "LLM_"}


class StorageSettings(BaseSettings):
    backend: str = "minio"                   # minio | oss | s3
    endpoint: str = "localhost:9000"
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "zhiqu-classroom"
    use_ssl: bool = False

    model_config = {"env_prefix": "STORAGE_"}


class AppSettings(BaseSettings):
    env: str = Field("dev", alias="APP_ENV")
    service_name: str = Field("unknown", alias="SERVICE_NAME")
    debug: bool = False
    log_level: str = "INFO"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440           # 24h

    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    llm: LLMSettings = LLMSettings()
    storage: StorageSettings = StorageSettings()


@lru_cache
def get_settings() -> AppSettings:
    """单例获取配置，进程内缓存"""
    return AppSettings()
```

### 4.4 配置使用规范

| 规则 | 说明 |
|------|------|
| 禁止硬编码 | 所有可变参数必须从 Settings 读取，禁止在业务代码中硬编码 URL / 端口 / 密钥 |
| 环境变量命名 | 全大写 + 下划线，前缀标识模块：`DB_HOST`, `REDIS_PORT`, `LLM_DEFAULT_MODEL` |
| 密钥注入 | 生产环境通过 K8s Secret / Docker Secret 挂载，不使用 `.env` 文件 |
| 配置校验 | 服务启动时 Pydantic 自动校验，缺失必填项直接 fast-fail |
| 文档同步 | 新增配置项必须同步更新 `.env.example` 和本文档 |

### 4.5 环境变量清单

| 变量 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `APP_ENV` | 否 | `dev` | 运行环境 |
| `SERVICE_NAME` | 是 | — | 服务名（日志标识） |
| `DB_HOST` | 是 | `localhost` | PostgreSQL 地址 |
| `DB_PORT` | 否 | `5432` | PostgreSQL 端口 |
| `DB_NAME` | 否 | `zhiqu_classroom` | 数据库名 |
| `DB_USER` | 是 | `postgres` | 数据库用户 |
| `DB_PASSWORD` | 是 | — | 数据库密码 |
| `DB_POOL_SIZE` | 否 | `10` | 连接池大小 |
| `REDIS_HOST` | 是 | `localhost` | Redis 地址 |
| `REDIS_PASSWORD` | 否 | — | Redis 密码 |
| `LLM_DEFAULT_PROVIDER` | 否 | `deepseek` | 默认 LLM 供应商 |
| `LLM_DEFAULT_MODEL` | 否 | `deepseek-v3` | 默认模型 |
| `LLM_REQUEST_TIMEOUT` | 否 | `60` | 调用超时(秒) |
| `STORAGE_BACKEND` | 否 | `minio` | 存储后端 |
| `STORAGE_ENDPOINT` | 是 | — | 对象存储地址 |
| `STORAGE_ACCESS_KEY` | 是 | — | 访问密钥 |
| `STORAGE_SECRET_KEY` | 是 | — | 私密密钥 |
| `JWT_SECRET` | 是 | — | JWT 签名密钥 |

---

## 5. 健康检查与优雅停机

### 5.1 健康检查端点

每个服务暴露以下端点（不走认证中间件）：

| 端点 | 用途 | 检查内容 |
|------|------|----------|
| `GET /healthz` | 存活探针（Liveness） | 进程存活即返回 200 |
| `GET /readyz` | 就绪探针（Readiness） | 依赖项全部可用返回 200 |

### 5.2 就绪检查项

```python
# services/shared/health/checker.py

import asyncio
from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class CheckResult:
    name: str
    status: Status
    latency_ms: int = 0
    message: str = ""


async def check_postgres(engine) -> CheckResult:
    """检查 PostgreSQL 连接"""
    import time
    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        ms = int((time.perf_counter() - start) * 1000)
        return CheckResult("postgres", Status.UP, ms)
    except Exception as e:
        ms = int((time.perf_counter() - start) * 1000)
        return CheckResult("postgres", Status.DOWN, ms, str(e))


async def check_redis(redis_client) -> CheckResult:
    import time
    start = time.perf_counter()
    try:
        await redis_client.ping()
        ms = int((time.perf_counter() - start) * 1000)
        return CheckResult("redis", Status.UP, ms)
    except Exception as e:
        ms = int((time.perf_counter() - start) * 1000)
        return CheckResult("redis", Status.DOWN, ms, str(e))


async def run_readiness_checks(engine, redis_client) -> dict:
    results = await asyncio.gather(
        check_postgres(engine),
        check_redis(redis_client),
    )
    overall = Status.UP if all(r.status == Status.UP for r in results) else Status.DOWN
    return {
        "status": overall.value,
        "checks": [
            {"name": r.name, "status": r.status.value,
             "latency_ms": r.latency_ms, "message": r.message}
            for r in results
        ],
    }
```

### 5.3 FastAPI 健康路由

```python
# services/shared/health/routes.py

from fastapi import APIRouter, Response
from .checker import run_readiness_checks

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness():
    return {"status": "up"}


@router.get("/readyz")
async def readiness(response: Response):
    # engine / redis_client 由 app.state 注入
    from fastapi import Request
    # 实际在 lifespan 中绑定依赖
    result = await run_readiness_checks(app_engine, app_redis)
    if result["status"] == "down":
        response.status_code = 503
    return result
```

响应示例（就绪）：

```json
{
  "status": "up",
  "checks": [
    { "name": "postgres", "status": "up", "latency_ms": 3, "message": "" },
    { "name": "redis", "status": "up", "latency_ms": 1, "message": "" }
  ]
}
```

### 5.4 优雅停机

```python
# services/shared/lifecycle.py

import signal
import asyncio
from contextlib import asynccontextmanager
from .config.settings import get_settings
from .logging.config import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan 管理器：启动初始化 + 优雅停机"""
    settings = get_settings()
    setup_logging(settings.service_name, level=settings.log_level)
    logger = get_logger("lifecycle")

    # ── 启动阶段 ──
    logger.info("服务启动", service=settings.service_name, env=settings.env)

    # 初始化数据库连接池
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(
        settings.db.async_url,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow,
    )
    app.state.db_engine = engine

    # 初始化 Redis
    import redis.asyncio as aioredis
    app.state.redis = aioredis.from_url(settings.redis.url)

    logger.info("资源初始化完成")

    yield  # ── 运行阶段 ──

    # ── 停机阶段 ──
    logger.info("开始优雅停机")

    # 1. 停止接收新请求（FastAPI 自动处理 SIGTERM）

    # 2. 等待进行中的请求完成（最长 30s）
    shutdown_timeout = 30

    # 3. 关闭 Redis 连接
    await app.state.redis.close()
    logger.info("Redis 连接已关闭")

    # 4. 关闭数据库连接池
    await engine.dispose()
    logger.info("数据库连接池已关闭")

    logger.info("服务已停止", service=settings.service_name)
```

### 5.5 Docker / K8s 配置

```yaml
# docker-compose 片段
services:
  content-engine:
    stop_grace_period: 30s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
```

```yaml
# K8s Deployment 片段（后期）
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 15
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
terminationGracePeriodSeconds: 30
```

---

## 6. 监控告警

### 6.1 可观测三支柱

| 支柱 | MVP 工具 | 后期演进 |
|------|----------|----------|
| 日志 (Logs) | structlog → Loki → Grafana | 同左（已稳定） |
| 指标 (Metrics) | Prometheus + FastAPI exporter | Prometheus + Thanos（长期存储） |
| 追踪 (Traces) | X-Request-ID 手动关联 | OpenTelemetry → Tempo/Jaeger |

### 6.2 Prometheus 指标暴露

```python
# services/shared/metrics/prometheus.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter

# ── 核心指标 ──

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

llm_call_total = Counter(
    "llm_call_total",
    "Total LLM API calls",
    ["service", "provider", "model", "task_type", "status"],
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM call latency",
    ["service", "provider", "model", "task_type"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["service", "provider", "model", "direction"],  # direction: input/output
)

db_pool_active = Gauge(
    "db_pool_active_connections",
    "Active database connections",
    ["service"],
)

redis_pool_active = Gauge(
    "redis_pool_active_connections",
    "Active Redis connections",
    ["service"],
)

# ── 指标暴露端点 ──

metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
```

### 6.3 指标采集中间件

```python
# services/shared/metrics/middleware.py

import time
from starlette.middleware.base import BaseHTTPMiddleware
from .prometheus import http_requests_total, http_request_duration_seconds
from ..config.settings import get_settings


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in ("/healthz", "/readyz", "/metrics"):
            return await call_next(request)

        service = get_settings().service_name
        method = request.method
        path = request.url.path

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        http_requests_total.labels(
            service=service, method=method,
            path=path, status_code=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            service=service, method=method, path=path,
        ).observe(duration)

        return response
```

### 6.4 告警规则

MVP 阶段使用 Grafana Alerting（内置，不需要单独部署 Alertmanager）。

| 告警名称 | 条件 | 严重级别 | 通知渠道 |
|----------|------|---------|----------|
| 服务宕机 | `/healthz` 连续 3 次失败 | Critical | 飞书群 webhook |
| 高错误率 | 5xx 比率 > 5%（5 分钟窗口） | Warning | 飞书群 webhook |
| LLM 调用失败率 | 失败率 > 10%（5 分钟窗口） | Warning | 飞书群 webhook |
| LLM 费用超限 | 单日费用超预设阈值 | Warning | 飞书群 webhook + 管理员 DM |
| 慢请求 | P95 延迟 > 5s（5 分钟窗口） | Warning | 飞书群 webhook |
| 数据库连接池耗尽 | 活跃连接 > 80% pool_size | Critical | 飞书群 webhook |
| Redis 连接异常 | readyz 中 Redis DOWN | Critical | 飞书群 webhook |
| 磁盘空间不足 | 使用率 > 85% | Warning | 飞书群 webhook |

### 6.5 Grafana Dashboard 规划

| Dashboard | 面板 | 数据源 |
|-----------|------|--------|
| 服务概览 | QPS、错误率、P50/P95/P99 延迟、活跃连接数 | Prometheus |
| LLM 用量 | 调用次数/成功率、Token 消耗、费用估算、模型对比 | Prometheus + PostgreSQL |
| 日志浏览 | 日志流、错误聚合、trace 查询 | Loki |
| 基础设施 | CPU/内存/磁盘/网络（node_exporter） | Prometheus |

### 6.6 MVP 监控部署

```yaml
# docker-compose.monitoring.yaml（独立 compose file）

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  loki:
    image: grafana/loki:2.9.0
    volumes:
      - loki_data:/loki
    ports:
      - "3100:3100"

  grafana:
    image: grafana/grafana:10.4.0
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}

volumes:
  prometheus_data:
  loki_data:
  grafana_data:
```

---

## 7. 审计日志

### 7.1 审计范围

审计日志记录**谁在什么时间对什么资源做了什么操作**，与业务日志分离存储。

| 类别 | 示例操作 |
|------|----------|
| 认证 | 登录、登出、Token 刷新、登录失败 |
| 用户管理 | 创建/禁用用户、修改角色、绑定监护人 |
| 内容管理 | 上传教材、发布/下架内容、修改知识点 |
| 任务管理 | 创建/发布/归档任务、批量分配 |
| LLM 管理 | 新增/修改 Provider、修改路由规则、模型上下线 |
| 系统配置 | 修改系统参数、导入导出数据 |

### 7.2 审计日志表

```sql
-- 审计日志（独立表，不做软删除）
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id        UUID,                            -- 操作人 ID（系统操作可为空）
    actor_type      VARCHAR(20) NOT NULL,            -- user / admin / system
    action          VARCHAR(50) NOT NULL,            -- login / create / update / delete / publish / archive
    resource_type   VARCHAR(50) NOT NULL,            -- user / textbook / task / model_config / ...
    resource_id     UUID,                            -- 目标资源 ID
    detail          JSONB DEFAULT '{}',              -- 变更详情（before/after diff）
    ip_address      VARCHAR(45),                     -- 客户端 IP（IPv4/IPv6）
    user_agent      VARCHAR(500),                    -- 客户端 UA
    trace_id        VARCHAR(64),                     -- 关联链路 ID
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_audit_actor     ON audit_logs(actor_id, created_at DESC);
CREATE INDEX idx_audit_action    ON audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_resource  ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created   ON audit_logs(created_at DESC);
```

### 7.3 审计日志 SDK

```python
# services/shared/audit/logger.py

from uuid import UUID
from datetime import datetime
from .models import AuditLog
from ..logging.config import get_logger

logger = get_logger("audit")


async def record_audit(
    session,
    *,
    actor_id: UUID | None,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    detail: dict | None = None,
    ip_address: str = "",
    user_agent: str = "",
    trace_id: str = "",
):
    """写入审计日志——业务层调用此函数"""
    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
        ip_address=ip_address,
        user_agent=user_agent,
        trace_id=trace_id,
    )
    session.add(log)
    await session.flush()

    logger.info(
        "审计记录",
        actor_id=str(actor_id),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
    )
    return log
```

### 7.4 使用示例

```python
# 在业务接口中
await record_audit(
    session,
    actor_id=current_user.id,
    actor_type="admin",
    action="update",
    resource_type="model_config",
    resource_id=model_id,
    detail={
        "before": {"status": "active"},
        "after": {"status": "disabled"},
        "fields_changed": ["status"],
    },
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent", ""),
    trace_id=trace_id_var.get(""),
)
```

### 7.5 审计日志查询（Admin API）

已在 `docs/api/admin.md` 中定义：

- `GET /api/v1/admin/audit/logs` — 分页查询，支持 `actor_id`, `action`, `resource_type`, `date_from`, `date_to` 过滤
- `GET /api/v1/admin/audit/logs/:id` — 查看单条审计详情

### 7.6 数据保留策略

| 阶段 | 策略 |
|------|------|
| MVP | 本地 PostgreSQL 存储，不做归档 |
| 增长期 | 6 个月热数据保留，超期数据按月导出到对象存储（JSON/Parquet） |
| 合规要求 | 根据实际法规要求调整保留年限（教育行业通常 3-5 年） |

---

## 8. 异步任务与重试

### 8.1 任务场景

| 任务类型 | 场景 | 耗时 | 优先级 |
|----------|------|------|--------|
| 教材解析 | 上传后解析 PDF/DOCX/PPTX → 结构化数据 | 10s-5min | 高 |
| 知识点抽取 | 解析后调用 LLM 抽取知识点 | 5s-30s | 高 |
| 游戏内容生成 | 基于知识点生成互动游戏 | 10s-60s | 中 |
| 视频脚本生成 | 生成教学视频脚本 + 分镜 | 15s-90s | 中 |
| 练习题生成 | 根据知识点批量生成练习题 | 5s-30s | 中 |
| 学习报告生成 | 聚合学习数据生成报告 | 5s-20s | 低 |
| 批量任务分配 | 年级/班级批量下发任务 | 1s-10s | 高 |

### 8.2 消息队列架构（Redis Streams）

```
Producer                     Redis Streams              Consumer Group
┌──────────┐  XADD          ┌──────────────┐  XREADGROUP  ┌──────────┐
│  API      │ ────────────► │ stream:tasks  │ ───────────► │ Worker 1 │
│  Handler  │               │               │              │          │
└──────────┘               │  (持久化)      │              └──────────┘
                            │               │  XREADGROUP  ┌──────────┐
                            └──────────────┘ ───────────► │ Worker 2 │
                                                           └──────────┘
```

### 8.3 任务生产者

```python
# services/shared/queue/producer.py

import json
import uuid
from datetime import datetime
from redis.asyncio import Redis


class TaskProducer:
    """任务生产者——向 Redis Stream 发送任务消息"""

    def __init__(self, redis: Redis, stream_prefix: str = "stream"):
        self.redis = redis
        self.stream_prefix = stream_prefix

    async def send(
        self,
        task_type: str,
        payload: dict,
        *,
        priority: str = "normal",
        delay_seconds: int = 0,
        max_retries: int = 3,
        trace_id: str = "",
    ) -> str:
        task_id = str(uuid.uuid4())
        stream_name = f"{self.stream_prefix}:{task_type}"

        message = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": json.dumps(payload, ensure_ascii=False),
            "priority": priority,
            "max_retries": str(max_retries),
            "retry_count": "0",
            "trace_id": trace_id or str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.redis.xadd(stream_name, message)
        return task_id
```

### 8.4 任务消费者

```python
# services/shared/queue/consumer.py

import json
import asyncio
import traceback
from redis.asyncio import Redis
from ..logging.config import get_logger

logger = get_logger("task_consumer")


class TaskConsumer:
    """任务消费者——从 Redis Stream 消费并处理任务"""

    def __init__(
        self,
        redis: Redis,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        handlers: dict,            # task_type → async handler function
        batch_size: int = 5,
        block_ms: int = 5000,
    ):
        self.redis = redis
        self.stream = stream_name
        self.group = group_name
        self.consumer = consumer_name
        self.handlers = handlers
        self.batch_size = batch_size
        self.block_ms = block_ms
        self._running = False

    async def _ensure_group(self):
        try:
            await self.redis.xgroup_create(
                self.stream, self.group, id="0", mkstream=True,
            )
        except Exception:
            pass  # group 已存在

    async def start(self):
        await self._ensure_group()
        self._running = True
        logger.info("消费者启动", stream=self.stream, group=self.group,
                     consumer=self.consumer)

        while self._running:
            try:
                messages = await self.redis.xreadgroup(
                    self.group, self.consumer,
                    {self.stream: ">"},
                    count=self.batch_size,
                    block=self.block_ms,
                )
                if not messages:
                    continue
                for stream_name, entries in messages:
                    for msg_id, data in entries:
                        await self._process(msg_id, data)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("消费循环异常", exc_info=True)
                await asyncio.sleep(1)

    async def _process(self, msg_id, data):
        task_type = data.get("task_type", "")
        task_id = data.get("task_id", "")
        retry_count = int(data.get("retry_count", 0))
        max_retries = int(data.get("max_retries", 3))
        trace_id = data.get("trace_id", "")

        handler = self.handlers.get(task_type)
        if not handler:
            logger.warning("未知任务类型", task_type=task_type, task_id=task_id)
            await self.redis.xack(self.stream, self.group, msg_id)
            return

        try:
            payload = json.loads(data.get("payload", "{}"))
            await handler(task_id=task_id, payload=payload, trace_id=trace_id)
            await self.redis.xack(self.stream, self.group, msg_id)
            logger.info("任务完成", task_type=task_type, task_id=task_id)
        except Exception:
            logger.error(
                "任务执行失败",
                task_type=task_type, task_id=task_id,
                retry_count=retry_count, max_retries=max_retries,
                exc_info=True,
            )
            if retry_count < max_retries:
                await self._retry(data, retry_count + 1)
            await self.redis.xack(self.stream, self.group, msg_id)

    async def _retry(self, data: dict, new_retry_count: int):
        """指数退避重试：重新投递到 stream"""
        retry_data = dict(data)
        retry_data["retry_count"] = str(new_retry_count)
        delay = min(2 ** new_retry_count, 60)  # 2s, 4s, 8s, ..., max 60s
        await asyncio.sleep(delay)
        await self.redis.xadd(self.stream, retry_data)
        logger.info("任务重试投递", task_id=data.get("task_id"),
                     retry_count=new_retry_count, delay_seconds=delay)

    def stop(self):
        self._running = False
```

### 8.5 重试策略

| 参数 | 值 | 说明 |
|------|------|------|
| 最大重试次数 | 3（默认） | 可在任务级别覆盖 |
| 退避策略 | 指数退避 `2^n` 秒 | 2s → 4s → 8s → ... |
| 最大退避 | 60 秒 | 避免过长等待 |
| 死信处理 | 超过最大重试 → 记录到 `failed_tasks` 表 | 人工排查 |
| 幂等性 | 每个任务携带 `task_id`，handler 需保证幂等 | 重复消费安全 |

### 8.6 失败任务表

```sql
CREATE TABLE failed_tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         VARCHAR(64) NOT NULL,
    task_type       VARCHAR(50) NOT NULL,
    payload         JSONB NOT NULL,
    error_message   TEXT,
    retry_count     INT NOT NULL DEFAULT 0,
    trace_id        VARCHAR(64),
    failed_at       TIMESTAMP NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMP,               -- 人工处理后标记
    resolved_by     UUID                     -- 处理人
);

CREATE INDEX idx_ft_type     ON failed_tasks(task_type, failed_at DESC);
CREATE INDEX idx_ft_resolved ON failed_tasks(resolved_at) WHERE resolved_at IS NULL;
```

### 8.7 使用示例

```python
# 在 API handler 中发送异步任务
producer = TaskProducer(redis=app.state.redis)

task_id = await producer.send(
    task_type="textbook_parse",
    payload={"textbook_id": str(textbook_id), "file_url": file_url},
    priority="high",
    max_retries=3,
    trace_id=trace_id_var.get(""),
)

return {"code": 0, "message": "ok", "data": {"task_id": task_id}}
```

### 8.8 后期演进

| 阶段 | 方案 | 说明 |
|------|------|------|
| MVP | Redis Streams | 简单可靠，零额外组件 |
| 增长期 | RabbitMQ | 延迟队列、死信交换、优先级队列 |
| 规模化 | Kafka | 高吞吐、事件溯源、多消费者组 |

迁移路径：保持 `TaskProducer` / `TaskConsumer` 接口不变，底层实现切换 adapter。

---

## 9. 安全基线

### 9.1 认证与授权

| 项目 | 规范 |
|------|------|
| 认证方式 | Bearer JWT（HS256 + 强密钥 ≥ 32 字符，后期可升级 RS256） |
| Token 有效期 | Access Token 24h，Refresh Token 7d |
| 登录方式 | 手机号 + 短信验证码（无密码） |
| 短信验证码 | 6 位数字，5 分钟有效，单号码 60s 发送限频 |
| 权限模型 | RBAC：`student` / `guardian` / `teacher` / `admin` / `super_admin` |
| 接口鉴权 | 除 `/healthz`, `/readyz`, `/metrics`, `/api/v1/auth/*` 外均需 Bearer Token |
| 管理接口 | `/api/v1/admin/*` 需 `admin` 或 `super_admin` 角色 |

### 9.2 输入验证

```python
# 所有 API 入参经过 Pydantic 模型严格校验
from pydantic import BaseModel, Field, constr
from uuid import UUID


class CreateTaskRequest(BaseModel):
    title: constr(min_length=1, max_length=200)
    task_type: str = Field(..., pattern=r"^(after_class|review|assessment)$")
    textbook_id: UUID
    chapter_id: UUID
    difficulty: str = Field("basic", pattern=r"^(basic|intermediate|advanced)$")
    estimated_duration_min: int = Field(ge=1, le=480)

    model_config = {"extra": "forbid"}  # 禁止额外字段
```

| 规则 | 说明 |
|------|------|
| 严格模式 | `extra = "forbid"`，拒绝未声明字段 |
| 长度限制 | 所有字符串字段设置 `max_length` |
| 范围约束 | 数值字段使用 `ge` / `le` / `gt` / `lt` |
| 枚举校验 | 枚举字段使用 `pattern` 或 `Literal` 类型 |
| SQL 注入 | ORM 参数化查询（SQLAlchemy），禁止字符串拼接 SQL |
| XSS | API 输出 JSON 无需额外处理；前端框架自动转义 |

### 9.3 速率限制

```python
# services/shared/security/rate_limit.py

from datetime import timedelta
from redis.asyncio import Redis


class RateLimiter:
    """基于 Redis 的滑动窗口限流"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(
        self,
        key: str,
        max_requests: int,
        window: timedelta,
    ) -> bool:
        """返回 True 允许，False 限流"""
        import time
        now = time.time()
        window_start = now - window.total_seconds()

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(window.total_seconds()) + 1)
        results = await pipe.execute()

        return results[2] <= max_requests
```

| 接口类别 | 限制 | 窗口 | Key 维度 |
|----------|------|------|----------|
| 短信验证码 | 1 次 | 60 秒 | IP + 手机号 |
| 登录尝试 | 5 次 | 5 分钟 | IP + 手机号 |
| 普通 API | 100 次 | 1 分钟 | User ID |
| LLM 生成 | 20 次 | 1 分钟 | User ID |
| Admin API | 200 次 | 1 分钟 | User ID |
| 文件上传 | 10 次 | 1 分钟 | User ID |

超限返回 `429 Too Many Requests` + `Retry-After` 响应头。

### 9.4 数据安全

| 项目 | 措施 |
|------|------|
| 传输加密 | 全链路 HTTPS / TLS 1.2+（MVP 内网可放宽） |
| 存储加密 | LLM API Key → AES-256-GCM 加密存储；JWT Secret → 环境变量注入 |
| 敏感日志 | 日志脱敏（见第 3 章），禁止记录明文密钥/完整手机号 |
| 文件安全 | 上传白名单：`pdf, docx, pptx, jpg, png`；大小限制 50MB |
| 对象存储 | Bucket 私有访问，预签名 URL（有效期 1h）分发 |
| 数据隔离 | 学生只能访问自己数据；教师限管辖班级 |
| 软删除 | 业务数据 `deleted_at` 软删除；物理删除需 super_admin 审批 |

### 9.5 CORS 配置

```python
# services/shared/security/cors.py

from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app, settings):
    if settings.env == "dev":
        origins = ["*"]
    else:
        origins = [
            "https://app.zhiqu-classroom.com",
            "https://admin.zhiqu-classroom.com",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "X-Request-ID", "X-Device-ID",
                        "Content-Type"],
        max_age=3600,
    )
```

### 9.6 安全响应头

```python
# services/shared/security/headers.py

from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Cache-Control"] = "no-store"
        return response
```

### 9.7 依赖安全

| 措施 | 说明 |
|------|------|
| 依赖锁定 | `poetry.lock` / `requirements.txt` 锁定精确版本 |
| 漏洞扫描 | CI 中运行 `pip-audit` 或 `safety check` |
| 最小权限 | Docker 容器使用非 root 用户运行 |
| 镜像安全 | 基础镜像 `python:3.12-slim`，定期更新 |
| Secret 扫描 | CI 中使用 `gitleaks` 检查代码泄漏密钥 |

### 9.8 安全检查清单

部署上线前逐项确认：

- [ ] 所有密钥通过环境变量 / Secret 注入，不在代码仓库中
- [ ] JWT Secret 长度 ≥ 32 字符
- [ ] 数据库密码强度达标，非默认密码
- [ ] HTTPS 已启用（含证书有效期监控）
- [ ] CORS 白名单已配置（生产环境不允许 `*`）
- [ ] 速率限制已生效
- [ ] 日志脱敏规则已验证
- [ ] 文件上传白名单和大小限制已配置
- [ ] Docker 容器非 root 运行
- [ ] `pip-audit` / `gitleaks` 零高危告警
- [ ] 管理接口已限制角色访问
- [ ] 审计日志覆盖关键操作

---

## 附录 A：中间件注册顺序

FastAPI 中间件按注册的 **逆序** 执行（最后注册的最先处理请求）。推荐注册顺序：

```python
# main.py — 中间件注册（顺序从上到下 = 执行从外到内）

from services.shared.security.cors import setup_cors
from services.shared.security.headers import SecurityHeadersMiddleware
from services.shared.logging.middleware import RequestLoggingMiddleware
from services.shared.metrics.middleware import MetricsMiddleware

# 1. CORS（最外层，先处理预检请求）
setup_cors(app, settings)

# 2. 安全响应头
app.add_middleware(SecurityHeadersMiddleware)

# 3. 请求日志（记录入口 + 出口）
app.add_middleware(RequestLoggingMiddleware)

# 4. Prometheus 指标采集
app.add_middleware(MetricsMiddleware)
```

## 附录 B：共享模块目录结构

```
services/shared/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py          # Pydantic Settings（第4章）
├── health/
│   ├── __init__.py
│   ├── checker.py            # 健康检查实现（第5章）
│   └── routes.py             # /healthz, /readyz 路由
├── lifecycle.py              # lifespan 管理器（第5章）
├── logging/
│   ├── __init__.py
│   ├── config.py             # structlog 配置（第3章）
│   ├── middleware.py          # 请求日志中间件
│   └── sanitizer.py          # 敏感字段脱敏
├── metrics/
│   ├── __init__.py
│   ├── prometheus.py          # 指标定义（第6章）
│   └── middleware.py          # 指标采集中间件
├── audit/
│   ├── __init__.py
│   ├── logger.py              # 审计日志 SDK（第7章）
│   └── models.py              # AuditLog ORM 模型
├── queue/
│   ├── __init__.py
│   ├── producer.py            # 任务生产者（第8章）
│   └── consumer.py            # 任务消费者
└── security/
    ├── __init__.py
    ├── cors.py                # CORS 配置（第9章）
    ├── headers.py             # 安全响应头
    └── rate_limit.py          # 速率限制
```
