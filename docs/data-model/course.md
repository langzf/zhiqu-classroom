# 课程域数据模型

> 对应服务：`content-engine`
> Schema 隔离：`content`

---

## 概述

课程域管理教材、章节、知识点及其向量表示，是教学内容的基础结构。支撑知识点提取、RAG 检索、资源生成等上层功能。

### 表清单

| 表名 | 说明 | 预估行数 |
|------|------|----------|
| `textbooks` | 教材主表 | 百级 |
| `chapters` | 教材章节树 | 千级 |
| `knowledge_points` | 知识点 | 万级 |
| `kp_embeddings` | 知识点向量 | 万级 |
| `generated_resources` | AI 生成资源 | 十万级 |
| `prompt_templates` | 提示词模板 | 百级 |

---

## 1. textbooks — 教材

```sql
CREATE TABLE textbooks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(200) NOT NULL,         -- 教材名称
    subject         VARCHAR(50)  NOT NULL,          -- 学科：math / chinese / english ...
    grade_range     VARCHAR(30)  NOT NULL,          -- 适用年级范围：grade_7-grade_9
    publisher       VARCHAR(100),                   -- 出版社
    edition         VARCHAR(50),                    -- 版本："2024人教版"
    cover_url       VARCHAR(500),                   -- 封面图 URL
    source_file_url VARCHAR(500),                   -- 原始文件 URL（PDF/DOCX）
    parse_status    VARCHAR(20)  NOT NULL DEFAULT 'pending',
                                                    -- pending / parsing / completed / failed
    metadata        JSONB        NOT NULL DEFAULT '{}',
                                                    -- 扩展元数据
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    version         INT          NOT NULL DEFAULT 1,
    deleted_at      TIMESTAMP,                      -- 软删除
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_textbooks_subject ON textbooks(subject);
CREATE INDEX idx_textbooks_grade   ON textbooks(grade_range);
CREATE INDEX idx_textbooks_status  ON textbooks(parse_status);
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `subject` | 学科标识，应用层枚举：`math`, `chinese`, `english`, `physics`, `chemistry`, `biology`, `history`, `geography`, `politics` |
| `grade_range` | 格式 `grade_{start}-grade_{end}`，如 `grade_7-grade_9` |
| `parse_status` | 教材解析状态：`pending`（待解析）→ `parsing`（解析中）→ `completed`（完成）/ `failed`（失败）|
| `metadata` | 灵活扩展字段，如 `{"total_pages": 280, "isbn": "978-...", "parse_model": "deepseek-v3"}` |

---

## 2. chapters — 章节

```sql
CREATE TABLE chapters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    textbook_id     UUID         NOT NULL,          -- ref: textbooks.id
    parent_id       UUID,                           -- 自引用，支持多级章节树
    title           VARCHAR(200) NOT NULL,
    sort_order      INT          NOT NULL DEFAULT 0,-- 同级排序
    level           INT          NOT NULL DEFAULT 1,-- 层级深度：1=章, 2=节, 3=小节
    page_start      INT,                            -- 起始页码
    page_end        INT,                            -- 结束页码
    metadata        JSONB        NOT NULL DEFAULT '{}',
    deleted_at      TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_chapters_textbook ON chapters(textbook_id, sort_order);
CREATE INDEX idx_chapters_parent   ON chapters(parent_id);
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `parent_id` | 为 NULL 时表示顶层章节；非 NULL 引用同表 `chapters.id`，构成递归树 |
| `level` | 章节深度：1=章、2=节、3=小节，便于查询特定层级 |
| `sort_order` | 同一 parent 下的排序序号 |

---

## 3. knowledge_points — 知识点

```sql
CREATE TABLE knowledge_points (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id      UUID         NOT NULL,          -- ref: chapters.id
    textbook_id     UUID         NOT NULL,          -- 冗余，加速教材级查询
    title           VARCHAR(200) NOT NULL,          -- 知识点标题
    content         TEXT,                           -- 知识点详细内容
    difficulty      VARCHAR(20)  NOT NULL DEFAULT 'basic',
                                                    -- basic / intermediate / advanced
    importance      INT          NOT NULL DEFAULT 3,-- 重要度 1-5
    prerequisites   JSONB        NOT NULL DEFAULT '[]',
                                                    -- 前置知识点 UUID 列表
    tags            JSONB        NOT NULL DEFAULT '[]',
                                                    -- 标签列表
    metadata        JSONB        NOT NULL DEFAULT '{}',
    sort_order      INT          NOT NULL DEFAULT 0,
    deleted_at      TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_kp_chapter    ON knowledge_points(chapter_id);
CREATE INDEX idx_kp_textbook   ON knowledge_points(textbook_id);
CREATE INDEX idx_kp_difficulty ON knowledge_points(difficulty);
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `difficulty` | 难度等级枚举：`basic`（基础）、`intermediate`（进阶）、`advanced`（拓展）|
| `importance` | 重要度 1-5，用于生成任务时的权重参考 |
| `prerequisites` | JSON 数组，存储前置知识点 UUID，如 `["uuid-1", "uuid-2"]` |
| `tags` | 标签数组，如 `["必考", "易错", "拓展"]` |

---

## 4. kp_embeddings — 知识点向量

```sql
CREATE TABLE kp_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_point_id UUID      NOT NULL,          -- ref: knowledge_points.id
    embedding       vector(1536) NOT NULL,          -- pgvector 向量（维度取决于模型）
    model_name      VARCHAR(100) NOT NULL,          -- 生成向量的模型名
    content_hash    VARCHAR(64)  NOT NULL,          -- 原文内容 SHA-256，用于判断是否需要重新生成
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX uniq_kpe_kp_model ON kp_embeddings(knowledge_point_id, model_name);
CREATE INDEX idx_kpe_embedding ON kp_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `embedding` | pgvector 类型，维度根据所选 Embedding 模型决定（OpenAI text-embedding-3-small = 1536，可调整）|
| `model_name` | 记录生成该向量的模型，支持多模型共存和模型切换后重新生成 |
| `content_hash` | 知识点内容的 SHA-256 摘要，当内容变更时触发向量重生成 |
| 唯一约束 | `(knowledge_point_id, model_name)` — 同一知识点同一模型只保留一条向量 |

### 向量索引说明

- 使用 `ivfflat` 索引类型（适合 MVP 数据量）
- `lists = 100`：适合万级数据量，数据增长后需调整
- 后期可切换到 `hnsw` 索引以获得更好的召回率

---

## 5. generated_resources — AI 生成资源

```sql
CREATE TABLE generated_resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type   VARCHAR(50)  NOT NULL,          -- 资源类型
    title           VARCHAR(200) NOT NULL,
    content         JSONB        NOT NULL,          -- 资源内容（结构化）
    textbook_id     UUID,                           -- ref: textbooks.id（可选）
    chapter_id      UUID,                           -- ref: chapters.id（可选）
    knowledge_points JSONB       NOT NULL DEFAULT '[]',
                                                    -- 关联知识点 UUID 列表
    difficulty      VARCHAR(20)  NOT NULL DEFAULT 'basic',
    target_grade    VARCHAR(20),                    -- 目标年级
    generation_params JSONB      NOT NULL DEFAULT '{}',
                                                    -- 生成参数快照
    quality_score   DECIMAL(3,2),                   -- 质量评分 0.00-1.00
    review_status   VARCHAR(20)  NOT NULL DEFAULT 'pending',
                                                    -- pending / approved / rejected
    reviewed_by     UUID,                           -- 审核人 ref: users.id
    reviewed_at     TIMESTAMP,
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    version         INT          NOT NULL DEFAULT 1,
    deleted_at      TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_gr_type       ON generated_resources(resource_type);
CREATE INDEX idx_gr_textbook   ON generated_resources(textbook_id);
CREATE INDEX idx_gr_chapter    ON generated_resources(chapter_id);
CREATE INDEX idx_gr_review     ON generated_resources(review_status);
CREATE INDEX idx_gr_difficulty ON generated_resources(difficulty);
```

### resource_type 枚举

| 值 | 说明 |
|------|------|
| `game` | 互动游戏 |
| `exercise` | 练习题 |
| `video_script` | 视频脚本 |
| `summary` | 知识点总结 |
| `mindmap` | 思维导图 |
| `flashcard` | 闪卡 |
| `quiz` | 随堂测验 |

### content JSONB Schema（按类型）

**游戏 (game)**
```json
{
  "game_type": "matching | sorting | fill_blank | quiz_battle",
  "instructions": "游戏说明文本",
  "elements": [
    {
      "question": "题目文本",
      "answer": "正确答案",
      "distractors": ["干扰项1", "干扰项2"],
      "hint": "提示信息"
    }
  ],
  "config": {
    "time_limit_sec": 300,
    "max_attempts": 3,
    "scoring_rule": "per_item | all_or_nothing"
  }
}
```

**练习题 (exercise)**
```json
{
  "questions": [
    {
      "type": "choice | fill_blank | short_answer | calculation",
      "stem": "题干文本",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "A",
      "explanation": "解析文本",
      "score": 5
    }
  ],
  "total_score": 100
}
```

**视频脚本 (video_script)**
```json
{
  "duration_sec": 180,
  "scenes": [
    {
      "scene_id": 1,
      "narration": "旁白文本",
      "visual_description": "画面描述",
      "duration_sec": 30,
      "keywords": ["关键词1", "关键词2"]
    }
  ],
  "style": "cartoon | whiteboard | live_action"
}
```

### generation_params JSONB Schema

```json
{
  "model": "deepseek-v3",
  "prompt_template_id": "uuid-...",
  "temperature": 0.7,
  "max_tokens": 4096,
  "knowledge_point_ids": ["uuid-1", "uuid-2"],
  "user_instructions": "用户附加要求",
  "llm_call_id": "uuid-..."
}
```

---

## 6. prompt_templates — 提示词模板

```sql
CREATE TABLE prompt_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,          -- 模板名称
    template_type   VARCHAR(50)  NOT NULL,          -- 模板用途类型
    content         TEXT         NOT NULL,           -- Jinja2 模板内容
    variables       JSONB        NOT NULL DEFAULT '[]',
                                                    -- 模板变量定义
    description     TEXT,                           -- 模板说明
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    version         INT          NOT NULL DEFAULT 1,
    created_by      UUID,                           -- ref: users.id
    deleted_at      TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX uniq_pt_name_ver ON prompt_templates(name, version)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_pt_type ON prompt_templates(template_type);
```

### template_type 枚举

| 值 | 说明 |
|------|------|
| `game_generate` | 游戏生成 |
| `exercise_generate` | 练习题生成 |
| `video_script_generate` | 视频脚本生成 |
| `knowledge_extract` | 知识点提取 |
| `quality_review` | 内容质量审核 |
| `summary_generate` | 总结生成 |
| `report_generate` | 报告生成 |

### variables JSONB Schema

```json
[
  {
    "name": "knowledge_points",
    "type": "list",
    "required": true,
    "description": "知识点列表"
  },
  {
    "name": "difficulty",
    "type": "string",
    "required": true,
    "description": "难度级别"
  },
  {
    "name": "target_grade",
    "type": "string",
    "required": false,
    "description": "目标年级"
  }
]
```

---

## 关系图

```
textbooks
├── chapters (textbook_id)
│   └── knowledge_points (chapter_id, textbook_id)
│       └── kp_embeddings (knowledge_point_id)
├── generated_resources (textbook_id, chapter_id)
└── prompt_templates (独立，通过 generation_params 关联)
```

## 常用查询

### 获取教材完整知识点树

```sql
SELECT c.title AS chapter_title, c.level,
       kp.title AS kp_title, kp.difficulty, kp.importance
FROM chapters c
JOIN knowledge_points kp ON kp.chapter_id = c.id
WHERE c.textbook_id = :textbook_id
  AND c.deleted_at IS NULL AND kp.deleted_at IS NULL
ORDER BY c.sort_order, kp.sort_order;
```

### 知识点语义检索 (RAG)

```sql
SELECT kp.id, kp.title, kp.content,
       1 - (e.embedding <=> :query_vector) AS similarity
FROM kp_embeddings e
JOIN knowledge_points kp ON kp.id = e.knowledge_point_id
WHERE e.model_name = :model_name AND kp.deleted_at IS NULL
ORDER BY e.embedding <=> :query_vector
LIMIT 10;
```