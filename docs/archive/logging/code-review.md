# 日志 Code Review 检查项

> 父文档：[README.md](./README.md)

---

## Code Review 检查清单

### 必须通过（Blocking）

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | 无 `print()` 调用 | 所有输出走 `structlog` |
| 2 | 无明文敏感信息 | 密码、Token、API Key 不能出现在日志中 |
| 3 | 异常日志带 `exc_info=True` | ERROR 级别异常必须附带堆栈 |
| 4 | 使用 KV 格式传参 | `logger.info("msg", key=value)` 而非字符串拼接 |
| 5 | 循环内无 INFO 日志 | 循环内使用 DEBUG |
| 6 | 接口有入口/出口日志 | 每个 API 至少 2 条 INFO |
| 7 | 外部调用有耗时记录 | HTTP/gRPC/LLM 调用记录 `duration_ms` |

### 建议改进（Non-blocking）

| # | 检查项 | 说明 |
|---|--------|------|
| 8 | logger 命名符合规范 | `{service}.{module}` 格式 |
| 9 | message 不含变量值 | 变量放 KV，message 保持稳定可搜索 |
| 10 | 适当的日志级别 | 不要所有日志都是 INFO |
| 11 | 大字段有截断 | SQL、请求体等长文本截断为前 500 字符 |
| 12 | 有降级/重试日志 | 降级用 WARNING，重试注明次数 |

## 常见问题示例

```python
# ❌ 字符串拼接
logger.info(f"用户 {user_id} 登录成功")

# ✅ KV 格式
logger.info("用户登录成功", user_id=user_id)

# ❌ INFO 循环日志
for item in items:
    logger.info("处理项目", item_id=item.id)

# ✅ DEBUG 循环日志 + INFO 汇总
for item in items:
    logger.debug("处理项目", item_id=item.id)
logger.info("批量处理完成", total=len(items), success=ok, failed=fail)

# ❌ 异常无堆栈
except Exception as e:
    logger.error(f"失败: {e}")

# ✅ 异常有堆栈
except Exception as e:
    logger.error("操作失败", error=str(e), exc_info=True)

# ❌ 明文密钥
logger.info("配置加载", api_key="sk-abcdefghijklmnop")

# ✅ 不记录或已脱敏
logger.info("配置加载", provider="deepseek", has_api_key=True)
```

## CI 自动检查

可在 CI 中添加静态检查规则：

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: no-print
      name: 禁止 print()
      entry: python -c "import sys; sys.exit(1 if 'print(' in open(sys.argv[1]).read() else 0)"
      language: system
      files: '\.py$'
      exclude: 'tests/|scripts/'

    - id: no-fstring-log
      name: 禁止 f-string 日志
      entry: 'grep -nP "logger\.\w+\(f\"" --include="*.py" -r services/'
      language: system
      pass_filenames: false
```
