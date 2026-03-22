# content-engine

## 职责
- 教材解析（PDF/Word/PPT/OCR文本）。
- 章节结构识别与知识点抽取。
- 知识点检索（RAG 索引）。

## 对外接口（示例）
- `POST /internal/textbooks/parse`
- `GET /internal/textbooks/:id/chapters`
- `GET /internal/knowledge-points/search?q=`

## 事件输出
- `textbook.parsed`
- `knowledge_points.generated`

## 数据归属
- 教材结构化结果。
- 知识点主数据。
- 检索索引元数据。

## 非职责
- 不负责最终学习任务编排。
- 不负责消息触达。
