# 敏感字段脱敏

> 父文档：[README.md](./README.md)

---

## 1. 脱敏规则

| 数据类型 | 规则 | 示例 |
|----------|------|------|
| 手机号 | 保留前 3 后 4 | `138****5678` |
| API Key | 保留前 6 后 4 | `sk-abc1...mnop` |
| Bearer Token | 保留前 10 | `Bearer ey...` → `Bearer ey********` |
| password / secret | 全部替换 | `***` |
| 身份证号 | 保留前 4 后 4 | `3101****5678` |
| 银行卡号 | 保留后 4 | `****5678` |
| email | @ 前保留首尾 | `z***g@example.com` |

## 2. 代码实现

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
    value = PHONE_RE.sub(
        lambda m: m.group()[:3] + "****" + m.group()[-4:], value
    )
    # 值内容匹配——API Key / Token
    value = KEY_RE.sub(lambda m: m.group()[:10] + "********", value)
    # 值内容匹配——邮箱
    value = EMAIL_RE.sub(
        lambda m: m.group(1) + "***" + m.group(3) + "@", value
    )
    return value


def sanitize_dict(data: dict) -> dict:
    """递归脱敏字典"""
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [
                sanitize_dict(i) if isinstance(i, dict)
                else sanitize_value(k, i) for i in v
            ]
        else:
            result[k] = sanitize_value(k, v)
    return result


def _sanitize_sensitive(logger, method_name, event_dict):
    """structlog processor：自动脱敏"""
    return sanitize_dict(event_dict)
```

## 3. 脱敏效果示例

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

## 4. 注意事项

- 脱敏 processor 放在 `format_exc_info` 之前，确保异常堆栈中的敏感值也被处理
- JSONB 类型字段（如 LLM `input_messages`）入库前需单独调用 `sanitize_dict`
- 脱敏规则可通过 `sys_configs` 表动态扩展，但核心规则硬编码确保兜底
