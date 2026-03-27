# P0 Task: AI 练习题生成

## 目标
基于已抽取的知识点，调用 LLM 自动生成不同类型的练习题，存入 `content.generated_resources`。

## 已有基础
- ✅ `GeneratedResource` / `PromptTemplate` 数据模型
- ✅ `LLMClient` 封装 (shared/llm_client.py)
- ✅ `KnowledgePoint` 模型及 CRUD
- ✅ init_db 已建好表

## Step 清单

### Step 1: Prompt 模板管理 CRUD
- [x] `services/content_engine/prompt_service.py`
  - 创建/更新/查询/激活 prompt 模板
  - 支持按 resource_type 查找当前激活的模板
- [x] router 里增加 `/prompts` 相关端点

### Step 2: 练习题生成 Service
- [x] `services/content_engine/exercise_service.py`
  - `generate_exercises(kp_id, exercise_type, count, difficulty)` 核心方法
  - 支持题型：choice（选择题）、fill_blank（填空题）、short_answer（简答题）、true_false（判断题）
  - 调用 LLMClient，用 prompt 模板 + 知识点信息构建请求
  - 解析 LLM 输出的 JSON 结构化题目
  - 存入 GeneratedResource
  - 简单的质量校验（字段完整性、答案存在等）

### Step 3: 练习题 API 端点
- [x] router 增加：
  - `POST /exercises/generate` — 生成练习题
  - `GET /exercises/{resource_id}` — 获取单套练习
  - `GET /knowledge-points/{kp_id}/exercises` — 按知识点查询练习
  - `GET /exercises` — 列表查询（支持 type/difficulty 筛选）

### Step 4: 默认 Prompt 模板种子数据
- [x] init_db.py 增加默认 prompt 模板
  - 选择题模板
  - 填空题模板
  - 简答题模板
  - 判断题模板

### Step 5: 测试验证
- [ ] 手动 curl/httpie 测试完整流程
  - 创建 prompt 模板 → 选择知识点 → 生成练习 → 查询结果

## 练习题 JSON Schema (content_json 字段)

```json
{
  "exercise_type": "choice",
  "questions": [
    {
      "id": 1,
      "stem": "题干文本",
      "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
      "answer": "B",
      "explanation": "解析文本",
      "difficulty": 3
    }
  ]
}
```
