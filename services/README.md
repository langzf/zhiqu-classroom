# 知趣课堂 - 后端服务

> 模块化单体，FastAPI + SQLAlchemy 2.0 async

## MVP 服务模块

| 模块 | 目录 | 职责 |
|------|------|------|
| 用户 | `user_profile/` | 认证、用户管理、家长绑定 |
| 内容 | `content_engine/` | 教材上传、解析、知识点、向量化 |
| AI 辅导 | `ai_tutor/` | 对话管理、RAG 检索增强 |
| 学习 | `learning_core/` | 学习任务、进度记录 |
| 共享 | `shared/` | 基类、统一响应、JWT、异常处理 |

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 代码约定

- 数据库主键: UUID v7
- 时间戳: UTC, `created_at` + `updated_at`
- 软删除: `deleted_at`
- API 路径: `/api/v1/{service}/{resource}`
- 统一响应: `{"code": 0, "message": "ok", "data": {...}}`
- 跨模块引用: UUID, 不建外键
