# API 接口文档（MVP）

> 最后更新：2026-03-26  
> 参考: [MVP-SCOPE.md](../MVP-SCOPE.md)

---

## 通用约定

- 路径：`/api/v1/{service}/{resource}`
- 资源用复数名词：`textbooks`, `chapters`, `knowledge-points`
- 嵌套资源最多两级：`/textbooks/:id/chapters`
- 动作用动词子路径：`/textbooks/:id/parse`
- 查询用 query params，创建/更新用 request body

## 模块索引（MVP）

| 文件 | 服务 | 说明 | 状态 |
|------|------|------|------|
| [user-auth.md](./user-auth.md) | user-profile | 认证 + 用户管理 | ✅ |
| [content-engine.md](./content-engine.md) | content-engine | 教材 + 知识点 | ✅ |
| [learning-orchestrator.md](./learning-orchestrator.md) | learning-core | 学习任务（简化版） | 🔧 需精简 |
| [ai-tutor/](./ai-tutor/README.md) | ai-tutor | AI 辅导对话 | ✅ |

## 归档的 API 文档

以下已移至 `archive/api/`，非 MVP 范围：

- `analytics.md` — 统计报表（P1 第二期）
- `media-generation.md` — 内容生成（P2）
- `admin.md` — 管理后台 26 接口（P1 第二期）
- `ai-tutor/feedback.md` — 反馈评价
- `ai-tutor/internal.md` — 内部接口
- `ai-tutor/stats.md` — 辅导统计
