# 日志系统设计文档（v1.0）

> 适用范围：zhiqu-classroom 全服务  
> 补充文档：platform-support.md §3 为概要版，本文档为完整设计  
> 最后更新：2026-03-25

---

## 目录

1. [设计目标与原则](#1-设计目标与原则)
2. [日志分类体系](#2-日志分类体系)
3. [日志级别规范](#3-日志级别规范)
4. [日志格式标准（JSON Schema）](#4-日志格式标准json-schema)
5. [链路追踪设计](#5-链路追踪设计)
6. [日志上下文注入机制](#6-日志上下文注入机制)
7. [敏感字段脱敏](#7-敏感字段脱敏)
8. [各场景日志规范](#8-各场景日志规范)
9. [LLM 调用专项日志](#9-llm-调用专项日志)
10. [异步任务日志](#10-异步任务日志)
11. [日志采集与存储架构](#11-日志采集与存储架构)
12. [日志查询与面板](#12-日志查询与面板)
13. [日志轮转与保留策略](#13-日志轮转与保留策略)
14. [代码实现参考](#14-代码实现参考)
15. [日志编写规约（Code Review 检查项）](#15-日志编写规约code-review-检查项)

---

## 1. 设计目标与原则

### 1.1 设计目标

| 目标 | 说明 |
|------|------|
| **全局统一** | 所有服务使用同一日志库（structlog）、同一格式（JSON）、同一上下文注入机制 |
| **结构化** | 全量 JSON 输出，每个字段有明确语义，便于机器解析和查询 |
| **链路贯通** | trace_id + span_id 串联完整请求链路，跨服务调用可追溯 |
| **自动化** | 通过中间件 + 装饰器自动注入上下文，业务代码零改动即可获得完整日志 |
| **安全脱敏** | 敏感信息在写入日志前自动脱敏 |
| **可观测** | 与 Prometheus 指标、Grafana 面板协同，构建完整可观测性体系 |
| **成本可控** | 合理的级别管控 + 采样策略，避免日志爆炸 |

### 1.2 设计原则

1. 日志是基础设施，不是事后补丁——架构设计时就规划好
2. 结构化 > 自由文本——永远用 KV 传参，不要拼接字符串
3. 上下文自动注入 > 手动传递——开发者不需要关心 trace_id 怎么来的
4. 脱敏在写入前完成——日志存储层看到的已经是安全数据
5. 开发环境可读 > JSON——本地开发用 ConsoleRenderer，线上用 JSON
6. 宁可多记不可漏记——关键节点必须有日志，但要控制粒度

---

## 2. 日志分类体系

### 2.1 按功能分类

| 类别 | 说明 | logger 命名 | 输出目标 |
|------|------|-------------|----------|
| **HTTP 访问日志** | 请求入口/出口，状态码、耗时 | `http.access` | stdout → Loki |
| **业务逻辑日志** | 核心业务流程关键节点 | `{service}.{module}` | stdout → Loki |
| **LLM 调用日志** | 模型调用详情（provider/token/cost） | `llm.call` | stdout → Loki + DB |
| **异步任务日志** | Celery 任务生命周期 | `task.{task_name}` | stdout → Loki |
| **安全审计日志** | 管理操作、权限变更 | `audit` | stdout → Loki + DB |
| **系统运维日志** | 健康检查、连接池、缓存命中 | `system.{component}` | stdout → Loki |

### 2.2 logger 命名规范

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

### 2.3 按持久化目标分类

| 日志类型 | stdout | Loki | 数据库 | 保留时间 |
|----------|--------|------|--------|----------|
| HTTP 访问日志 | ✅ | ✅ | ❌ | 30天 |
| 业务逻辑日志 | ✅ | ✅ | ❌ | 30天 |
| LLM 调用日志 | ✅ | ✅ | ✅ `llm_call_logs` | Loki 30天 / DB 6个月 |
| 异步任务日志 | ✅ | ✅ | ✅ `task_executions` | Loki 30天 / DB 6个月 |
| 审计日志 | ✅ | ✅ | ✅ `audit_logs` | Loki 30天 / DB 永久 |
| 系统运维日志 | ✅ | ✅ | ❌ | 14天 |

---

## 3. 日志级别规范

### 3.1 级别定义

| 级别 | 数值 | 使用场景 | 示例 |
|------|------|----------|------|
| **DEBUG** | 10 | 开发调试细节，生产环境默认关闭 | 变量值、循环内单条处理、SQL 语句 |
| **INFO** | 20 | 业务流程关键节点（入口/出口/状态变更） | 请求开始/完成、任务启动/结束、LLM 调用成功 |
| **WARNING** | 30 | 可自愈的异常、降级操作、接近阈值 | LLM 降级、限流触发、配置缺失用默认值 |
| **ERROR** | 40 | 不可自愈的业务异常，需要人工关注 | LLM 调用失败、数据库操作异常、外部服务不可用 |
| **CRITICAL** | 50 | 系统级致命错误，服务无法继续 | 数据库连接池耗尽、所有 LLM provider 不可用 |

### 3.2 级别使用规则

```python
# ✅ DEBUG — 循环内、调试详情
for chapter in chapters:
    logger.debug("处理章节", chapter_id=chapter.id, page_start=chapter.start)

# ✅ INFO — 关键节点，每个请求至少 2 条（入口 + 出口）
logger.info("开始解析教材", textbook_id=tid, file_type="pdf")
logger.info("教材解析完成", textbook_id=tid, chapters=12, duration_ms=1523)

# ✅ WARNING — 降级、重试、接近阈值
logger.warning("LLM 主力超时，降级到备选", primary="deepseek-v3", fallback="qwen-2.5-72b")
logger.warning("日费用接近上限", current=85.5, limit=100.0, usage_pct=85.5)

# ✅ ERROR — 必须附带 exc_info=True
try:
    result = await llm.complete(messages)
except Exception as e:
    logger.error("LLM 调用失败", provider="deepseek", model="deepseek-v3", exc_info=True)
    raise

# ✅ CRITICAL — 致命错误
logger.critical("数据库连接池耗尽", pool_size=20, active=20, waiting=15)
```

### 3.3 生产环境级别配置

| 环境 | 默认级别 | 特殊配置 |
|------|----------|----------|
| 本地开发 | DEBUG | ConsoleRenderer（彩色可读） |
| 测试环境 | DEBUG | JSONRenderer（验证格式） |
| 预发布 | INFO | 同生产 |
| 生产 | INFO | 可通过 `sys_configs` 动态调整单个 logger 级别 |

**动态级别调整：**

```python
# 通过管理 API 临时开启某模块 DEBUG
PUT /api/v1/admin/log-level
{
    "logger": "content_engine.textbook_parser",
    "level": "DEBUG",
    "duration_minutes": 30  # 30 分钟后自动恢复
}
```

---

## 4. 日志格式标准（JSON Schema）

### 4.1 基础字段（所有日志必须包含）

```json
{
  "timestamp": "2026-03-25T14:30:00.123+08:00",
  "level": "INFO",
  "logger": "content_engine.textbook_parser",
  "message": "教材解析完成",
  "service": "content-engine",
  "instance": "content-engine-pod-abc12",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "span_id": "1234abcd",
  "parent_span_id": "",
  "user_id": "",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 4.2 字段说明

| 字段 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
| `timestamp` | string | ✅ | structlog 自动 | ISO 8601 带时区 |
| `level` | string | ✅ | structlog 自动 | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `logger` | string | ✅ | get_logger() 参数 | logger 名称 |
| `message` | string | ✅ | 第一个位置参数 | 事件描述（简短、可搜索） |
| `service` | string | ✅ | 环境变量 SERVICE_NAME | 服务名 |
| `instance` | string | ✅ | HOSTNAME / Pod Name | 实例标识 |
| `trace_id` | string | ✅ | X-Request-ID 或自动生成 | 请求链路 ID |
| `span_id` | string | ✅ | 每个服务入口生成 | 当前跨度 ID |
| `parent_span_id` | string | ❌ | 上游传递 | 父跨度 ID |
| `user_id` | string | ❌ | JWT 解析 | 当前用户 |
| `request_id` | string | ✅ | 等同 trace_id | 向后兼容 |

### 4.3 扩展字段（按场景附加）

#### HTTP 请求日志

```json
{
  "...基础字段...",
  "method": "POST",
  "path": "/api/v1/textbooks/parse",
  "query_string": "",
  "client_ip": "10.0.1.100",
  "status_code": 200,
  "duration_ms": 1523,
  "request_size": 2048,
  "response_size": 512,
  "user_agent": "Mozilla/5.0 ..."
}
```

#### LLM 调用日志

```json
{
  "...基础字段...",
  "llm_provider": "deepseek",
  "llm_model": "deepseek-v3",
  "task_type": "knowledge_extract",
  "input_tokens": 1500,
  "output_tokens": 800,
  "total_tokens": 2300,
  "cost_yuan": 0.0023,
  "llm_latency_ms": 3200,
  "is_fallback": false,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

#### 异步任务日志

```json
{
  "...基础字段...",
  "task_name": "content_engine.textbook_parse",
  "task_id": "celery-uuid-123",
  "task_status": "success",
  "retry_count": 0,
  "queue": "content",
  "execution_ms": 45000,
  "triggered_by": "user-uuid"
}
```

#### 审计操作日志

```json
{
  "...基础字段...",
  "audit_action": "update",
  "resource_type": "model_config",
  "resource_id": "model-uuid-456",
  "operator_id": "admin-uuid",
  "operator_name": "张老师",
  "ip_address": "10.0.1.50",
  "changes": {
    "before": { "temperature": 0.7 },
    "after": { "temperature": 0.3 }
  }
}
```

### 4.4 message 字段规范

`message` 是日志的核心可搜索字段，遵循以下规范：

```
规则：
  1. 使用中文（团队一致性）
  2. 简短明确，动宾结构：「开始解析教材」「LLM 调用失败」「任务超时」
  3. 不包含变量值——变量放到 KV 字段中
  4. 同一事件不同位置使用不同 message（可区分入口/出口）

✅ 好的 message：
  "开始解析教材"          ← 配合 textbook_id=xxx
  "教材解析完成"          ← 配合 chapters=12, duration_ms=1523
  "LLM 调用降级"          ← 配合 primary=xxx, fallback=xxx
  "请求完成"              ← 配合 status_code=200, duration_ms=50

❌ 差的 message：
  "开始解析教材 abc-123"  ← 变量值不应拼进 message
  "done"                  ← 含义不明
  "error occurred"        ← 英文（团队统一用中文）
  "处理"                  ← 太笼统
```

---

## 5. 链路追踪设计

### 5.1 追踪模型

```
            trace_id (全局唯一，整条请求链路共享)
            ┌──────────────────────────────────────┐
            │                                      │
  ┌─────────┴──────────┐   ┌────────────────────┐  │
  │ span_id: aa11      │   │ span_id: bb22      │  │
  │ parent: (none)     │──▶│ parent: aa11       │  │
  │ service: user-     │   │ service: content-  │  │
  │   profile          │   │   engine           │  │
  └────────────────────┘   └────────┬───────────┘  │
                                    │              │
                           ┌────────┴───────────┐  │
                           │ span_id: cc33      │  │
                           │ parent: bb22       │  │
                           │ service: LLM call  │  │
                           └────────────────────┘  │
            └──────────────────────────────────────┘
```

### 5.2 trace_id 生成与传递

```
1. 客户端发起请求，可携带 X-Request-ID
2. API 网关（Nginx/Traefik）：
   - 如果有 X-Request-ID → 透传
   - 如果没有 → 生成 UUID v4，写入 X-Request-ID
3. FastAPI 中间件：
   - 从 X-Request-ID 读取 → 设为 trace_id
   - 生成 span_id（8 位 hex）
   - 注入 contextvars
4. 服务间调用：
   - HTTP Header 传递 X-Request-ID + X-Span-ID
   - 被调用方读取 → trace_id 复用，parent_span_id 设为上游 span_id
5. 响应头：
   - 返回 X-Trace-ID（方便客户端/前端定位问题）
```

### 5.3 contextvars 定义

```python
# services/shared/logging/context.py

from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
parent_span_id_var: ContextVar[str] = ContextVar("parent_span_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
```

### 5.4 span_id 生成

```python
import secrets

def generate_span_id() -> str:
    """8 位 hex，足够在单 trace 内唯一"""
    return secrets.token_hex(4)

def generate_trace_id() -> str:
    """UUID v4 格式"""
    import uuid
    return str(uuid.uuid4())
```

---

## 6. 日志上下文注入机制

### 6.1 注入时机与来源

| 上下文字段 | 注入时机 | 来源 |
|------------|----------|------|
| `service` | 进程启动 | `SERVICE_NAME` 环境变量 |
| `instance` | 进程启动 | `HOSTNAME` 或 `socket.gethostname()` |
| `trace_id` | 请求入口 | `X-Request-ID` Header 或自动生成 |
| `span_id` | 请求入口 | 自动生成 |
| `parent_span_id` | 请求入口 | `X-Span-ID` Header（跨服务调用） |
| `user_id` | JWT 解析后 | Token payload |
| `request_id` | 请求入口 | 等同 trace_id |

### 6.2 structlog Processor 链

```python
# services/shared/logging/config.py

import structlog
import os

def setup_logging(json_output: bool = True, log_level: str = "INFO"):
    """初始化 structlog，服务启动时调用一次"""

    processors = [
        structlog.contextvars.merge_contextvars,   # 自动合并 contextvars
        _add_service_context,                       # 注入 service/instance
        _add_trace_context,                         # 注入 trace/span
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        _sanitize_sensitive,                        # 脱敏处理
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_service_context(logger, method_name, event_dict):
    event_dict.setdefault("service", os.environ.get("SERVICE_NAME", "unknown"))
    event_dict.setdefault("instance", os.environ.get("HOSTNAME", "unknown"))
    return event_dict


def _add_trace_context(logger, method_name, event_dict):
    from .context import trace_id_var, span_id_var, parent_span_id_var, user_id_var
    event_dict.setdefault("trace_id", trace_id_var.get(""))
    event_dict.setdefault("span_id", span_id_var.get(""))
    event_dict.setdefault("parent_span_id", parent_span_id_var.get(""))
    event_dict.setdefault("user_id", user_id_var.get(""))
    return event_dict
```

### 6.3 获取 logger

```python
# 业务代码中使用
import structlog

logger = structlog.get_logger("content_engine.textbook_parser")

# 自动附带 service, instance, trace_id, span_id, user_id 等
logger.info("教材解析完成", textbook_id="xxx", chapters=12, duration_ms=1523)
```

---

## 7. 敏感字段脱敏

### 7.1 脱敏规则

| 数据类型 | 规则 | 示例 |
|----------|------|------|
| 手机号 | 保留前 3 后 4 | `138****1234` |
| API Key | 保留前 6 后 4 | `sk-abc1...xyz9` |
| Bearer Token | 保留前 10 | `Bearer ey...` → `Bearer ey********` |
| password / secret | 全部替换 | `***` |
| 身份证号 | 保留前 4 后 4 | `3101****5678` |
| 银行卡号 | 保留后 4 | `****5678` |
| email | @ 前保留首尾 | `z***g@example.com` |

### 7.2 脱敏实现

```python
# services/shared/logging/sanitizer.py

import re
from typing import Any

# 字段名匹配（不区分大小写）
SENSITIVE_KEYS = {
    "password", "secret", "api_key", "token", "authorization",
    "api_key_encrypted", "refresh_token", "access_token",
    "id_card", "bank_card", "credential",
}

# 值匹配正则
PHONE_RE = re.compile(r'1[3-9]\d{9}')
KEY_RE = re.compile(r'(sk-|ak-|Bearer\s+)\S{8,}')
EMAIL_RE = re.compile(r'([a-zA-Z0-9])([a-zA-Z0-9.]*?)([a-zA-Z0-9])@')


def sanitize_value(key: str, value: Any) -> Any:
    """按字段名脱敏"""
    if not isinstance(value, str):
        return value

    key_lower = key.lower()

    # 字段名在敏感集合中
    if any(sk in key_lower for sk in SENSITIVE_KEYS):
        if len(value) <= 6:
            return "***"
        return value[:6] + "..." + value[-4:]

    # 值内容匹配——手机号
    value = PHONE_RE.sub(lambda m: m.group()[:3] + "****" + m.group()[-4:], value)

    # 值内容匹配——API Key / Token
    value = KEY_RE.sub(lambda m: m.group()[:10] + "********", value)

    # 值内容匹配——邮箱
    value = EMAIL_RE.sub(lambda m: m.group(1) + "***" + m.group(3) + "@", value)

    return value


def sanitize_dict(data: dict) -> dict:
    """递归脱敏字典"""
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [sanitize_dict(i) if isinstance(i, dict) else sanitize_value(k, i) for i in v]
        else:
            result[k] = sanitize_value(k, v)
    return result


def _sanitize_sensitive(logger, method_name, event_dict):
    """structlog processor：自动脱敏"""
    return sanitize_dict(event_dict)
```

### 7.3 脱敏效果示例

```json
// 脱敏前
{
  "message": "用户登录",
  "phone": "13812345678",
  "api_key": "sk-abcdefghijklmnop",
  "password": "my_secret_123"
}

// 脱敏后
{
  "message": "用户登录",
  "phone": "138****5678",
  "api_key": "sk-abc1...mnop",
  "password": "***"
}
```
