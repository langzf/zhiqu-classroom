# analytics-reporting

## 职责
- 学习数据聚合统计。
- 看板指标与报表输出。
- 后期支持个性化分析输入特征计算。

## 对外接口（示例）
- `GET /internal/reports/student/:id/weekly`
- `GET /internal/metrics/content-usage`

## 事件输入
- `task.completed`
- `learning.recorded`

## 数据归属
- 统计宽表与报表快照。

## 非职责
- 不作为实时交易链路主服务。
