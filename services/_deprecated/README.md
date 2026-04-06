# _deprecated/

旧模块目录归档。这些目录在 Phase 6 步骤 3（2026-03-30）从 `services/` 根目录迁移至此。

## 已迁移的旧模块（含完整代码）
- `ai_tutor/` — AI 辅导模块（旧）
- `content_engine/` — 内容引擎模块（旧）
- `learning_core/` — 学习核心模块（旧）
- `learning_orchestrator/` — 学习编排模块（旧）
- `user_profile/` — 用户档案模块（旧）

## 已迁移的占位目录（仅含 README）
- `content-engine/` — 横杠命名占位
- `learning-orchestrator/` — 横杠命名占位
- `user-profile/` — 横杠命名占位
- `analytics-reporting/` — 未实现的预留模块
- `media-generation/` — 未实现的预留模块
- `notification/` — 未实现的预留模块
- `api-gateway/` — 未实现的预留模块

## 新架构对应
所有功能已迁移至分层架构：
- `infrastructure/` — 持久化、外部服务
- `application/` — 业务服务层
- `interfaces/` — API 路由 + Schemas
- `shared/` — 公共工具

确认新架构稳定运行后，可安全删除此目录。
