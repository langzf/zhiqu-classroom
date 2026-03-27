# 审计日志

> 父文档：[README.md](./README.md)

---

## 1. 概述

记录系统中关键操作的完整审计轨迹，用于安全合规、问题追溯和行为分析。审计日志一经写入不可修改，不可软删除。

## 2. 数据模型

表 `audit_logs`：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| trace_id | VARCHAR(64) | NOT NULL | 请求链路 ID |
| operator_id | UUID | NOT NULL | 操作人用户 ID |
| operator_role | VARCHAR(20) | NOT NULL | 操作时角色 |
| action | VARCHAR(100) | NOT NULL | 操作动作（点分命名） |
| resource_type | VARCHAR(50) | NOT NULL | 资源类型 |
| resource_id | VARCHAR(100) | NULL | 资源 ID |
| changes | JSONB | NULL | 变更前后对比 |
| ip_address | VARCHAR(50) | NULL | 客户端 IP |
| user_agent | VARCHAR(500) | NULL | 客户端 UA |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |
| created_at | TIMESTAMP | NOT NULL | 操作时间 |

### 索引

| 索引名 | 字段 | 说明 |
|--------|------|------|
| `idx_audit_operator` | operator_id | 按操作人查询 |
| `idx_audit_action` | action | 按动作类型查询 |
| `idx_audit_resource` | (resource_type, resource_id) | 按资源查询 |
| `idx_audit_created` | created_at | 时间范围查询 |

### 分区策略

与 `llm_call_logs` 一致，按 `created_at` 月份分区，保留 12 个月热数据，冷数据归档至对象存储。

## 3. 审计动作清单

### 认证与权限

| action | 说明 |
|--------|------|
| `auth.login` | 用户登录 |
| `auth.logout` | 用户登出 |
| `auth.login_failed` | 登录失败 |
| `auth.token_refresh` | Token 刷新 |
| `auth.role_change` | 角色变更 |

### 用户管理

| action | 说明 |
|--------|------|
| `user.create` | 创建用户 |
| `user.update` | 更新用户信息 |
| `user.disable` | 禁用用户 |
| `user.delete` | 删除用户（软删除） |

### 内容管理

| action | 说明 |
|--------|------|
| `content.textbook.upload` | 上传教材 |
| `content.textbook.parse` | 触发教材解析 |
| `content.task.create` | 创建任务 |
| `content.task.publish` | 发布任务 |
| `content.task.archive` | 归档任务 |

### LLM 管理

| action | 说明 |
|--------|------|
| `llm.provider.create` | 新增 Provider |
| `llm.provider.update` | 更新 Provider |
| `llm.provider.delete` | 删除 Provider |
| `llm.model.create` | 新增模型配置 |
| `llm.model.status_change` | 模型状态变更 |
| `llm.routing.update` | 路由规则变更 |

### 系统配置

| action | 说明 |
|--------|------|
| `config.update` | 配置值变更 |
| `config.refresh` | 缓存手动刷新 |

## 4. 审计服务

```python
# services/shared/audit.py

from datetime import datetime
from uuid import uuid4


class AuditService:
    """审计日志服务 — 只写不改"""

    def __init__(self, db_session, logger):
        self.db = db_session
        self.logger = logger

    async def log(
        self,
        action: str,
        resource_type: str,
        operator_id: str,
        operator_role: str,
        resource_id: str = None,
        changes: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        metadata: dict = None,
    ):
        """写入审计记录"""
        from contextvars import copy_context
        trace_id = trace_id_var.get("")

        record = AuditLog(
            id=uuid4(),
            trace_id=trace_id,
            operator_id=operator_id,
            operator_role=operator_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            created_at=datetime.now(),
        )

        self.db.add(record)
        await self.db.flush()

        self.logger.info(
            "审计记录",
            audit_action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            operator_id=operator_id,
        )
```

### 中间件自动采集

```python
# 在请求中间件中自动注入审计上下文
class AuditMiddleware:
    """对写操作自动记录审计日志"""

    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def __call__(self, request, call_next):
        response = await call_next(request)

        if (
            request.method in self.AUDIT_METHODS
            and response.status_code < 400
            and self._should_audit(request.url.path)
        ):
            await self.audit_service.log(
                action=self._resolve_action(request.method, request.url.path),
                resource_type=self._resolve_resource_type(request.url.path),
                operator_id=request.state.user_id,
                operator_role=request.state.user_role,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
            )

        return response
```

## 5. 查询 API

```
GET    /api/v1/admin/audit-logs                  🔑  审计日志列表（分页）
GET    /api/v1/admin/audit-logs/:id             🔑  审计日志详情
```

### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| page | INT | 页码 |
| page_size | INT | 每页条数 |
| operator_id | UUID | 筛选操作人 |
| action | STRING | 筛选动作（支持前缀匹配，如 `llm.*`） |
| resource_type | STRING | 筛选资源类型 |
| resource_id | STRING | 筛选资源 ID |
| start_time | DATETIME | 起始时间 |
| end_time | DATETIME | 截止时间 |

## 6. 安全约束

- 审计表 **不提供** UPDATE / DELETE API
- 数据库层面可通过 `REVOKE DELETE, UPDATE ON audit_logs FROM app_user` 防止应用层误删
- 归档到对象存储时保留原始文件哈希（SHA256），确保不可篡改
- 管理后台审计页面需要 `admin` 角色权限
