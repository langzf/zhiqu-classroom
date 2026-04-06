# media-generation

## 职责
- 基于知识点生成 AI 游戏配置。
- 生成短视频脚本/分镜建议。
- 生成分层练习题集。

## 对外接口（示例）
- `POST /internal/media/game/generate`
- `POST /internal/media/video-script/generate`
- `POST /internal/media/practice/generate`

## 输入依赖
- 知识点数据（来自 `content-engine`）。
- 模板与策略参数（来自配置中心/后台）。

## 数据归属
- 生成内容版本记录。
- 质量评分与审核状态。

## 非职责
- 不直接管理学生学习进度。
