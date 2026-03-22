# learning-orchestrator

## 职责
- 课后任务编排与状态流转。
- 学生学习流程执行（开始/完成/复习）。
- 后期承接诊断、周课程表与复盘流程。

## 对外接口（示例）
- `POST /internal/tasks/publish`
- `POST /internal/tasks/:id/start`
- `POST /internal/tasks/:id/complete`
- `GET /internal/students/:id/tasks`

## 事件输入
- `knowledge_points.generated`
- `media.generated`

## 事件输出
- `task.published`
- `task.completed`
- `learning.recorded`

## 数据归属
- 任务实例与任务状态。
- 学习过程流水记录（首期基础版）。

## 非职责
- 不负责教材解析和内容生成算法本身。
