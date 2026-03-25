# API 接口文档

> zhiqu-classroom 全量 API 设计  
> 最后更新：2026-03-25

---

## 通用约定

通用规范（响应格式、错误码、分页、认证）见 [api-spec.md](../api-spec.md) 前半部分。

## 模块索引

| 文件 | 服务 | 接口数 | 状态 |
|------|------|--------|------|
| [../api-spec.md](../api-spec.md) | 认证 + 用户（auth / user-profile） | 12 | ✅ |
| [content-engine.md](./content-engine.md) | 教材 + 知识点（content-engine） | 16 | ✅ |
| [media-generation.md](./media-generation.md) | 内容生成（media-generation） | 13 | ✅ |
| [learning-orchestrator.md](./learning-orchestrator.md) | 学习编排（learning-orchestrator） | 16 | ✅ |
| [analytics.md](./analytics.md) | 统计报表 + 通知（analytics） | 12 | ✅ |
| [ai-tutor/](./ai-tutor/README.md) | AI 辅导（ai-tutor） | 12 | ✅ |
| [admin.md](./admin.md) | 管理后台（admin） | 26 | ✅ |

## 接口命名规范

- 路径：`/api/v1/{service}/{resource}`
- 资源用复数名词：`textbooks`, `chapters`, `knowledge-points`
- 嵌套资源最多两级：`/textbooks/:id/chapters`
- 动作用动词子路径：`/textbooks/:id/parse`
- 查询用 query params，创建/更新用 request body
