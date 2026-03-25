# 日志级别规范

> 父文档：[README.md](./README.md)

---

## 1. 级别定义

| 级别 | 数值 | 使用场景 | 示例 |
|------|------|----------|------|
| **DEBUG** | 10 | 开发调试细节，生产环境默认关闭 | 变量值、循环内单条处理、SQL 语句 |
| **INFO** | 20 | 业务流程关键节点（入口/出口/状态变更） | 请求开始/完成、任务启动/结束 |
| **WARNING** | 30 | 可自愈的异常、降级操作、接近阈值 | LLM 降级、限流触发、配置缺失 |
| **ERROR** | 40 | 不可自愈的业务异常，需人工关注 | LLM 调用失败、数据库异常 |
| **CRITICAL** | 50 | 系统级致命错误，服务无法继续 | 连接池耗尽、全部 provider 不可用 |

## 2. 级别使用规则

```python
# ✅ DEBUG — 循环内、调试详情
for chapter in chapters:
    logger.debug("处理章节", chapter_id=chapter.id, page_start=chapter.start)

# ✅ INFO — 关键节点，每个请求至少 2 条（入口 + 出口）
logger.info("开始解析教材", textbook_id=tid, file_type="pdf")
logger.info("教材解析完成", textbook_id=tid, chapters=12, duration_ms=1523)

# ✅ WARNING — 降级、重试、接近阈值
logger.warning("LLM 主力超时，降级到备选",
    primary="deepseek-v3", fallback="qwen-2.5-72b")
logger.warning("日费用接近上限",
    current=85.5, limit=100.0, usage_pct=85.5)

# ✅ ERROR — 必须附带 exc_info=True
try:
    result = await llm.complete(messages)
except Exception as e:
    logger.error("LLM 调用失败",
        provider="deepseek", model="deepseek-v3", exc_info=True)
    raise

# ✅ CRITICAL — 致命错误
logger.critical("数据库连接池耗尽",
    pool_size=20, active=20, waiting=15)
```

## 3. 生产环境级别配置

| 环境 | 默认级别 | 特殊配置 |
|------|----------|----------|
| 本地开发 | DEBUG | ConsoleRenderer（彩色可读） |
| 测试环境 | DEBUG | JSONRenderer（验证格式） |
| 预发布 | INFO | 同生产 |
| 生产 | INFO | 可动态调整单个 logger 级别 |

## 4. 动态级别调整

通过管理 API 临时开启某模块 DEBUG（排查问题用）：

```python
# PUT /api/v1/admin/log-level
{
    "logger": "content_engine.textbook_parser",
    "level": "DEBUG",
    "duration_minutes": 30  # 30 分钟后自动恢复 INFO
}
```

实现方式：写入 `sys_configs` 表 + 定时器恢复。
