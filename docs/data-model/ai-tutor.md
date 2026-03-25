# AI 辅导域数据模型

> 对应服务：`ai-tutor`
> Schema 隔离：`tutor`

---

## 概述

AI 辅导域管理学生与 AI 助教的对话交互，支撑答疑、学习指导、知识点讲解等场景。对话按会话组织，每条消息记录角色、内容及关联的知识点上下文。

### 表清单

| 表名 | 说明 | 预估行数 |
|------|------|----------|
| `conversations` | 对话会话 | 十万级 |
| `messages` | 对话消息 | 百万级 |

---

## 1. conversations — 对话会话

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID         NOT NULL,           -- ref: users.id
    title           VARCHAR(200),                    -- 会话标题（可自动生成）
    scene           VARCHAR(50)  NOT NULL DEFAULT 'free_chat',
                                                     -- 对话场景
    context         JSONB        NOT NULL DEFAULT '{}',
                                                     -- 上下文信息
    status          VARCHAR(20)  NOT NULL DEFAULT 'active',
                                                     -- active / archived
    message_count   INT          NOT NULL DEFAULT 0, -- 消息计数（冗余，减少 COUNT 查询）
    last_message_at TIMESTAMP,                       -- 最新消息时间
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_conv_student ON conversations(student_id, updated_at DESC);
CREATE INDEX idx_conv_scene   ON conversations(scene);
```

### scene 枚举

| 值 | 说明 |
|------|------|
| `free_chat` | 自由问答 |
| `homework_help` | 作业辅导（关联特定任务）|
| `concept_explain` | 知识点讲解 |
| `review_guide` | 复习指导 |
| `error_analysis` | 错题分析 |

### context JSONB Schema

```json
{
  "task_id": "uuid-...",
  "chapter_id": "uuid-...",
  "knowledge_point_ids": ["uuid-1", "uuid-2"],
  "difficulty": "basic",
  "student_grade": "grade_8",
  "system_prompt_override": null
}
```

---

## 2. messages — 对话消息

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID         NOT NULL,           -- ref: conversations.id
    role            VARCHAR(20)  NOT NULL,            -- user / assistant / system
    content         TEXT         NOT NULL,             -- 消息内容
    content_type    VARCHAR(30)  NOT NULL DEFAULT 'text',
                                                     -- text / image / audio / mixed
    attachments     JSONB        NOT NULL DEFAULT '[]',
                                                     -- 附件列表
    token_count     INT,                             -- Token 消耗（assistant 消息）
    model_name      VARCHAR(100),                    -- 使用的模型名（assistant 消息）
    llm_call_id     UUID,                            -- ref: llm_call_logs.id
    feedback        JSONB,                           -- 用户反馈
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_msg_conv ON messages(conversation_id, created_at);
CREATE INDEX idx_msg_role ON messages(conversation_id, role);
```

### role 说明

| 值 | 说明 |
|------|------|
| `system` | 系统提示词（通常第一条，对用户不可见）|
| `user` | 学生消息 |
| `assistant` | AI 助教回复 |

### attachments JSONB Schema

```json
[
  {
    "type": "image",
    "url": "https://oss.example.com/uploads/photo.jpg",
    "thumbnail_url": "https://oss.example.com/uploads/photo_thumb.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 204800
  }
]
```

### feedback JSONB Schema

```json
{
  "rating": "helpful | unhelpful",
  "comment": "解释得很清楚",
  "reported": false,
  "reported_reason": null,
  "timestamp": "2024-03-15T10:30:00+08:00"
}
```

---

## 关系图

```
conversations (student_id → users.id)
└── messages (conversation_id)
    └── → llm_call_logs.id (可选关联)
```

## 设计要点

### 上下文管理

AI 辅导对话需要维护上下文窗口。实现策略：

1. **滑动窗口**：每次调用 LLM 时取最近 N 条消息（默认 20 条）
2. **知识注入**：根据 `context.knowledge_point_ids` 从 RAG 检索相关知识片段，注入 system prompt
3. **摘要压缩**：对话超过阈值时，用 LLM 生成中间摘要替代早期消息

### Token 控制

- `messages.token_count` 记录每条 AI 回复的 token 消耗
- 通过 `conversations.message_count` 快速判断对话长度
- 超长对话自动触发摘要（阈值在 `sys_configs` 中配置）

---

## 常用查询

### 获取对话历史（带分页）

```sql
SELECT id, role, content, content_type, attachments, feedback, created_at
FROM messages
WHERE conversation_id = :conversation_id
ORDER BY created_at ASC
LIMIT :page_size OFFSET :offset;
```

### 学生最近对话列表

```sql
SELECT id, title, scene, message_count, last_message_at, status
FROM conversations
WHERE student_id = :student_id
  AND status = 'active'
ORDER BY updated_at DESC
LIMIT 20;
```

### AI 回答质量统计

```sql
SELECT
    DATE(m.created_at) AS dt,
    COUNT(*) AS total_replies,
    COUNT(*) FILTER (WHERE m.feedback->>'rating' = 'helpful') AS helpful,
    COUNT(*) FILTER (WHERE m.feedback->>'rating' = 'unhelpful') AS unhelpful
FROM messages m
WHERE m.role = 'assistant'
  AND m.feedback IS NOT NULL
  AND m.created_at >= now() - interval '30 days'
GROUP BY DATE(m.created_at)
ORDER BY dt DESC;
```
