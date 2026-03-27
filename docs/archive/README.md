# 归档文档

> ⚠️ 此目录存放非 MVP 范围或已被取代的文档，仅供参考和后期恢复。

---

## MVP 精简归档（2026-03-26）

以下文档在 MVP 精简中从活跃目录移入，**功能完整可直接恢复**：

### API 文档

| 文件 | 原路径 | 恢复优先级 |
|------|--------|-----------|
| api/analytics.md | api/analytics.md | P1（第二期） |
| api/media-generation.md | api/media-generation.md | P2 |
| api/admin.md | api/admin.md | P1（第二期） |
| api/ai-tutor-feedback.md | api/ai-tutor/feedback.md | P2 |
| api/ai-tutor-internal.md | api/ai-tutor/internal.md | P2 |
| api/ai-tutor-stats.md | api/ai-tutor/stats.md | P2 |

### 数据模型

| 文件 | 原路径 | 恢复优先级 |
|------|--------|-----------|
| data-model/analytics.md | data-model/analytics.md | P1 |
| data-model/llm-ops.md | data-model/llm-ops.md | P2 |
| data-model/learning-engine.md | data-model/learning-engine.md | P1 |
| data-model/platform/ | data-model/platform/ | P1 |

### 完整子系统

| 目录 | 说明 | 恢复优先级 |
|------|------|-----------|
| frontend/ | 前端三端页面规格（50+ 页面） | 按需 |
| logging/ | 完整日志设计（12 子模块） | P2 |
| platform/ | 平台支撑（审计、通知、配置、异步任务，8 子模块） | P1 |

---

## 历史归档（结构重组前）

| 文件 | 原用途 | 替代文档 |
|------|--------|----------|
| data-model.md | 早期数据模型（单体文件） | data-model/ 分域目录 |
| api-spec.md | 早期 API 约定 + 认证接口 | api/ 分模块目录 |
| ai-education-app-initial.md | 初始需求 / 头脑风暴 | architecture/ 架构文档 |
| platform-support.md | 平台支撑分析 | architecture/service-detail.md |
| logging-design.md | 早期日志设计（单体文件） | logging/ 分模块目录 |

---

## 恢复指南

恢复某个模块时：
1. 将对应文件从 `archive/` 移回原路径
2. 更新父目录的 `README.md` 索引
3. 更新 `docs/STRUCTURE.md` 文档树
4. 更新 `docs/MVP-SCOPE.md` 的「不做清单」
