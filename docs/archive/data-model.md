# 核心数据模型设计（v1.0）

> 适用范围：zhiqu-classroom MVP 阶段
> 数据库：PostgreSQL 16 + pgvector

---

## 1. 设计原则

- 每个服务拥有独立 schema（逻辑隔离），首期共享同一 PostgreSQL 实例
- 跨服务引用只存 ID，不建外键约束
- 所有表包含 `created_at`, `updated_at` 审计字段
- 软删除使用 `deleted_at` (nullable timestamp)
- 主键统一使用 UUID v7（时间有序，分布式友好）
- 枚举值在应用层定义，数据库用 `VARCHAR` 存储

---

## 2. user-profile 服务

### 2.1 users（用户主表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 用户 ID |
| phone | VARCHAR(20) | UNIQUE, NOT NULL | 手机号（登录凭证） |
| password_hash | VARCHAR(128) | NULL | 密码哈希（预留，首期用短信验证码） |
| nickname | VARCHAR(50) | NOT NULL | 昵称 |
| avatar_url | VARCHAR(500) | NULL | 头像 URL |
| role | VARCHAR(20) | NOT NULL | 枚举: `student` / `parent` / `teacher` / `admin` |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 枚举: `active` / `disabled` / `pending` |
| last_login_at | TIMESTAMP | NULL | 最后登录时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | |
| deleted_at | TIMESTAMP | NULL | |

**索引：**
- `idx_users_phone` ON (phone) WHERE deleted_at IS NULL
- `idx_users_role` ON (role)

### 2.2 student_profiles（学生档案）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, UNIQUE | 一对一关联用户 |
| grade | VARCHAR(20) | NOT NULL | 年级，如 `grade_7` / `grade_8` |
| school_name | VARCHAR(100) | NULL | 学校名称 |
| enrollment_year | INT | NULL | 入学年份 |
| subjects | JSONB | DEFAULT '[]' | 已选学科列表 `["math", "physics"]` |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

### 2.3 guardian_bindings（家长-学生绑定）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| parent_user_id | UUID | NOT NULL | 家长 user_id |
| student_user_id | UUID | NOT NULL | 学生 user_id |
| relation | VARCHAR(20) | NOT NULL | 枚举: `father` / `mother` / `guardian` / `other` |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 枚举: `active` / `revoked` |
| created_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_guardian_parent` ON (parent_user_id)
- `idx_guardian_student` ON (student_user_id)
- `uniq_guardian_pair` UNIQUE ON (parent_user_id, student_user_id)

### 2.4 refresh_tokens（刷新令牌）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL | |
| token_hash | VARCHAR(128) | UNIQUE, NOT NULL | refresh token 哈希 |
| device_info | VARCHAR(200) | NULL | 设备标识 |
| expires_at | TIMESTAMP | NOT NULL | 过期时间 |
| revoked_at | TIMESTAMP | NULL | 撤销时间 |
| created_at | TIMESTAMP | NOT NULL | |

---

## 3. content-engine 服务

### 3.1 textbooks（教材）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| title | VARCHAR(200) | NOT NULL | 教材名称 |
| subject | VARCHAR(50) | NOT NULL | 学科: `math` / `physics` / `chemistry` 等 |
| grade | VARCHAR(20) | NOT NULL | 年级 |
| publisher | VARCHAR(100) | NULL | 出版社 |
| edition | VARCHAR(50) | NULL | 版本/版次 |
| source_file_url | VARCHAR(500) | NOT NULL | 原文件 OSS 地址 |
| source_type | VARCHAR(20) | NOT NULL | 枚举: `pdf` / `docx` / `pptx` / `image` / `text` |
| parse_status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 枚举: `pending` / `parsing` / `completed` / `failed` |
| parse_error | TEXT | NULL | 解析失败原因 |
| parsed_at | TIMESTAMP | NULL | 解析完成时间 |
| uploaded_by | UUID | NOT NULL | 上传者 user_id |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |
| deleted_at | TIMESTAMP | NULL | |

**索引：**
- `idx_textbooks_subject_grade` ON (subject, grade)
- `idx_textbooks_parse_status` ON (parse_status)

### 3.2 chapters（章节）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| textbook_id | UUID | FK → textbooks.id, NOT NULL | |
| parent_id | UUID | NULL | 父章节 ID（支持多级） |
| title | VARCHAR(200) | NOT NULL | 章节标题 |
| sort_order | INT | NOT NULL, DEFAULT 0 | 排序序号 |
| level | INT | NOT NULL, DEFAULT 1 | 层级深度（1=章, 2=节, 3=小节） |
| raw_content | TEXT | NULL | 原始提取文本 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_chapters_textbook` ON (textbook_id, sort_order)
- `idx_chapters_parent` ON (parent_id)

### 3.3 knowledge_points（知识点）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| chapter_id | UUID | FK → chapters.id, NOT NULL | 所属章节 |
| textbook_id | UUID | NOT NULL | 冗余，便于按教材查询 |
| name | VARCHAR(200) | NOT NULL | 知识点名称 |
| definition | TEXT | NULL | 定义描述 |
| difficulty | VARCHAR(20) | NOT NULL, DEFAULT 'basic' | 枚举: `basic` / `intermediate` / `advanced` |
| key_terms | JSONB | DEFAULT '[]' | 关键术语列表 |
| common_mistakes | JSONB | DEFAULT '[]' | 常见错误列表 |
| prerequisites | JSONB | DEFAULT '[]' | 先修知识点 ID 列表 |
| sort_order | INT | NOT NULL, DEFAULT 0 | |
| review_status | VARCHAR(20) | NOT NULL, DEFAULT 'auto' | 枚举: `auto` / `reviewed` / `rejected` |
| reviewed_by | UUID | NULL | 审核人 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_kp_chapter` ON (chapter_id)
- `idx_kp_textbook` ON (textbook_id)
- `idx_kp_difficulty` ON (difficulty)

### 3.4 knowledge_point_embeddings（知识点向量索引）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| knowledge_point_id | UUID | FK → knowledge_points.id, NOT NULL | |
| chunk_text | TEXT | NOT NULL | 切片文本内容 |
| chunk_index | INT | NOT NULL, DEFAULT 0 | 片段序号 |
| embedding | VECTOR(1024) | NOT NULL | bge-large-zh-v1.5 向量 |
| metadata | JSONB | DEFAULT '{}' | 额外元信息（学科、年级、难度等） |
| created_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_kpe_kp` ON (knowledge_point_id)
- `idx_kpe_embedding` USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)

---

## 4. media-generation 服务

### 4.1 generated_resources（生成资源主表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| knowledge_point_id | UUID | NOT NULL | 关联知识点（跨服务 ID） |
| resource_type | VARCHAR(30) | NOT NULL | 枚举: `game_quiz` / `game_drag_match` / `video_script` / `practice_set` |
| title | VARCHAR(200) | NOT NULL | 资源标题 |
| content | JSONB | NOT NULL | 生成内容（结构化 JSON，Schema 见 4.2） |
| difficulty | VARCHAR(20) | NOT NULL | 枚举: `basic` / `intermediate` / `advanced` |
| version | INT | NOT NULL, DEFAULT 1 | 内容版本号 |
| quality_score | DECIMAL(3,2) | NULL | 自动质量评分 (0.00-1.00) |
| review_status | VARCHAR(20) | NOT NULL, DEFAULT 'auto' | 枚举: `auto` / `approved` / `rejected` |
| reviewed_by | UUID | NULL | 审核人 |
| prompt_template_id | VARCHAR(100) | NULL | 使用的 Prompt 模板标识 |
| llm_model | VARCHAR(100) | NULL | 使用的 LLM 模型 |
| generation_cost_ms | INT | NULL | 生成耗时（毫秒） |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_gr_kp` ON (knowledge_point_id)
- `idx_gr_type` ON (resource_type)
- `idx_gr_kp_type` ON (knowledge_point_id, resource_type)

### 4.2 content JSONB Schema（按 resource_type）

#### game_quiz（选择闯关）
```json
{
  "levels": [
    {
      "level_no": 1,
      "question": "一元二次方程的一般形式是？",
      "options": ["ax²+bx+c=0", "ax+b=0", "ax³+bx=0", "a/x+b=0"],
      "correct_index": 0,
      "explanation": "标准形式为 ax²+bx+c=0 (a≠0)",
      "difficulty": "basic"
    }
  ],
  "total_levels": 5,
  "time_limit_sec": 300
}
```

#### game_drag_match（拖拽配对）
```json
{
  "pairs": [
    { "left": "判别式", "right": "b²-4ac", "hint": "判断根的情况" },
    { "left": "韦达定理", "right": "x₁+x₂=-b/a", "hint": "根与系数的关系" }
  ],
  "distractor_rights": ["x₁·x₂=-c/a"],
  "time_limit_sec": 180
}
```

#### video_script（视频脚本）
```json
{
  "duration_sec": 60,
  "scenes": [
    {
      "scene_no": 1,
      "duration_sec": 15,
      "narration": "今天我们来学习一元二次方程...",
      "visual_description": "黑板动画，公式逐步出现",
      "subtitle_key_points": ["一元二次方程", "一般形式"],
      "asset_prompts": ["chalkboard animation formula reveal"]
    }
  ],
  "total_scenes": 4
}
```

#### practice_set（练习题集）
```json
{
  "questions": [
    {
      "question_no": 1,
      "type": "single_choice",
      "stem": "下列哪个是一元二次方程？",
      "options": ["x²+2x+1=0", "2x+3=0", "x³=8", "1/x=2"],
      "correct_answer": "A",
      "explanation": "最高次为 2 且只有一个未知数",
      "difficulty": "basic"
    },
    {
      "question_no": 2,
      "type": "fill_blank",
      "stem": "方程 x²-5x+6=0 的两根之和为 ____",
      "correct_answer": "5",
      "explanation": "由韦达定理 x₁+x₂ = -b/a = 5",
      "difficulty": "intermediate"
    }
  ],
  "total_questions": 10
}
```

### 4.3 prompt_templates（Prompt 模板）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(100) | PK | 模板标识，如 `math.basic.game_quiz.v1` |
| resource_type | VARCHAR(30) | NOT NULL | |
| subject | VARCHAR(50) | NOT NULL | 学科 |
| grade_range | VARCHAR(50) | NULL | 适用年级范围，如 `grade_7-grade_9` |
| template_content | TEXT | NOT NULL | Jinja2 模板内容 |
| variables | JSONB | DEFAULT '[]' | 模板变量说明 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| version | INT | NOT NULL, DEFAULT 1 | |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

---

## 5. learning-orchestrator 服务

### 5.1 tasks（课后任务）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| title | VARCHAR(200) | NOT NULL | 任务标题 |
| description | TEXT | NULL | 任务说明 |
| textbook_id | UUID | NOT NULL | 关联教材（跨服务 ID） |
| chapter_id | UUID | NULL | 关联章节 |
| target_knowledge_points | JSONB | NOT NULL, DEFAULT '[]' | 目标知识点 ID 列表 |
| resource_refs | JSONB | NOT NULL, DEFAULT '[]' | 关联资源 ID 列表（game/video/practice） |
| task_type | VARCHAR(30) | NOT NULL, DEFAULT 'after_class' | 枚举: `after_class` / `review` / `assessment` |
| difficulty | VARCHAR(20) | NOT NULL, DEFAULT 'basic' | |
| estimated_duration_min | INT | NULL | 预估完成时长（分钟） |
| published_by | UUID | NOT NULL | 发布者 user_id |
| published_at | TIMESTAMP | NULL | 发布时间 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | 枚举: `draft` / `published` / `archived` |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_tasks_textbook` ON (textbook_id)
- `idx_tasks_status` ON (status)

### 5.2 task_assignments（任务分配）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | FK → tasks.id, NOT NULL | |
| student_user_id | UUID | NOT NULL | 分配给哪个学生 |
| assign_type | VARCHAR(20) | NOT NULL | 枚举: `individual` / `class` / `grade` |
| assigned_at | TIMESTAMP | NOT NULL | |
| due_at | TIMESTAMP | NULL | 截止时间 |

**索引：**
- `idx_ta_task` ON (task_id)
- `idx_ta_student` ON (student_user_id)
- `uniq_ta` UNIQUE ON (task_id, student_user_id)

### 5.3 learning_records（学习记录流水）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | NOT NULL | 所属任务 |
| student_user_id | UUID | NOT NULL | 学生 |
| resource_id | UUID | NOT NULL | 学习的资源 |
| resource_type | VARCHAR(30) | NOT NULL | 资源类型 |
| status | VARCHAR(20) | NOT NULL | 枚举: `started` / `in_progress` / `completed` / `abandoned` |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP | NULL | 完成时间 |
| duration_sec | INT | NULL | 实际学习时长（秒） |
| score | DECIMAL(5,2) | NULL | 得分（练习/游戏） |
| max_score | DECIMAL(5,2) | NULL | 满分 |
| accuracy | DECIMAL(3,2) | NULL | 正确率 (0.00-1.00) |
| answers | JSONB | NULL | 详细答题记录 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `idx_lr_task` ON (task_id)
- `idx_lr_student` ON (student_user_id)
- `idx_lr_student_resource` ON (student_user_id, resource_type)
- `idx_lr_created` ON (created_at)

### 5.4 task_progress（任务完成进度）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | NOT NULL | |
| student_user_id | UUID | NOT NULL | |
| total_resources | INT | NOT NULL | 任务包含的资源总数 |
| completed_resources | INT | NOT NULL, DEFAULT 0 | 已完成资源数 |
| overall_status | VARCHAR(20) | NOT NULL, DEFAULT 'not_started' | 枚举: `not_started` / `in_progress` / `completed` |
| overall_accuracy | DECIMAL(3,2) | NULL | 综合正确率 |
| first_started_at | TIMESTAMP | NULL | 首次开始时间 |
| completed_at | TIMESTAMP | NULL | 全部完成时间 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `uniq_tp` UNIQUE ON (task_id, student_user_id)
- `idx_tp_student_status` ON (student_user_id, overall_status)

---

## 6. analytics-reporting 服务

### 6.1 daily_study_stats（每日学习统计）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| student_user_id | UUID | NOT NULL | |
| stat_date | DATE | NOT NULL | 统计日期 |
| study_duration_sec | INT | NOT NULL, DEFAULT 0 | 学习总时长 |
| tasks_completed | INT | NOT NULL, DEFAULT 0 | 完成任务数 |
| resources_completed | INT | NOT NULL, DEFAULT 0 | 完成资源数 |
| games_played | INT | NOT NULL, DEFAULT 0 | 游戏次数 |
| videos_watched | INT | NOT NULL, DEFAULT 0 | 视频观看数 |
| practices_done | INT | NOT NULL, DEFAULT 0 | 练习完成数 |
| avg_accuracy | DECIMAL(3,2) | NULL | 平均正确率 |
| knowledge_points_covered | INT | NOT NULL, DEFAULT 0 | 涉及知识点数 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

**索引：**
- `uniq_dss` UNIQUE ON (student_user_id, stat_date)
- `idx_dss_date` ON (stat_date)

### 6.2 weekly_reports（周报快照）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| student_user_id | UUID | NOT NULL | |
| week_start | DATE | NOT NULL | 周开始日期（周一） |
| week_end | DATE | NOT NULL | 周结束日期（周日） |
| report_data | JSONB | NOT NULL | 结构化报告内容 |
| generated_at | TIMESTAMP | NOT NULL | 生成时间 |
| sent_to_parent | BOOLEAN | DEFAULT false | 是否已推送家长 |
| created_at | TIMESTAMP | NOT NULL | |

**report_data JSONB Schema：**
```json
{
  "summary": {
    "active_days": 4,
    "total_duration_min": 180,
    "tasks_completed": 6,
    "avg_accuracy": 0.75
  },
  "subject_breakdown": [
    {
      "subject": "math",
      "duration_min": 120,
      "accuracy": 0.72,
      "kp_mastered": ["kp_001", "kp_003"],
      "kp_weak": ["kp_005"]
    }
  ],
  "highlights": ["连续4天完成课后任务", "一元二次方程正确率提升15%"],
  "suggestions": ["建议加强判别式应用题练习"]
}
```

**索引：**
- `uniq_wr` UNIQUE ON (student_user_id, week_start)

### 6.3 content_usage_stats（内容使用统计）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| resource_id | UUID | NOT NULL | 资源 ID |
| resource_type | VARCHAR(30) | NOT NULL | |
| knowledge_point_id | UUID | NOT NULL | |
| total_views | INT | NOT NULL, DEFAULT 0 | 总使用次数 |
| total_completions | INT | NOT NULL, DEFAULT 0 | 完成次数 |
| avg_accuracy | DECIMAL(3,2) | NULL | 平均正确率 |
| avg_duration_sec | INT | NULL | 平均用时 |
| stat_date | DATE | NOT NULL | 统计日期 |
| created_at | TIMESTAMP | NOT NULL | |

**索引：**
- `uniq_cus` UNIQUE ON (resource_id, stat_date)
- `idx_cus_kp` ON (knowledge_point_id)

---

## 7. ER 关系总览

```
┌─────────────────────────────────────────────────────────────────┐
│                       user-profile schema                       │
│                                                                 │
│  users ──1:1──> student_profiles                                │
│    │                                                            │
│    ├──1:N──> refresh_tokens                                     │
│    │                                                            │
│    └──M:N──> guardian_bindings (parent ↔ student)               │
└─────────────────────────────────────────────────────────────────┘
        │ user_id (跨服务引用, 无 FK)
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     content-engine schema                        │
│                                                                 │
│  textbooks ──1:N──> chapters ──1:N──> knowledge_points          │
│                                           │                     │
│                                           └──1:N──> kp_embeddings│
└─────────────────────────────────────────────────────────────────┘
        │ knowledge_point_id (跨服务引用)
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    media-generation schema                       │
│                                                                 │
│  generated_resources (content JSONB 按 resource_type 变化)       │
│  prompt_templates                                               │
└─────────────────────────────────────────────────────────────────┘
        │ resource_id, task_id (跨服务引用)
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  learning-orchestrator schema                    │
│                                                                 │
│  tasks ──1:N──> task_assignments                                │
│    │                                                            │
│    ├──1:N──> learning_records                                   │
│    │                                                            │
│    └──1:N──> task_progress                                      │
└─────────────────────────────────────────────────────────────────┘
        │ 学习数据聚合
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  analytics-reporting schema                      │
│                                                                 │
│  daily_study_stats                                              │
│  weekly_reports                                                 │
│  content_usage_stats                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. 枚举值汇总

| 枚举名 | 值 | 使用表 |
|--------|-----|--------|
| user_role | `student`, `parent`, `teacher`, `admin` | users.role |
| user_status | `active`, `disabled`, `pending` | users.status |
| grade | `grade_1` ~ `grade_12` | student_profiles.grade, textbooks.grade |
| subject | `math`, `physics`, `chemistry`, `biology`, `chinese`, `english`, `history`, `geography`, `politics` | textbooks.subject, knowledge_points (via textbook) |
| guardian_relation | `father`, `mother`, `guardian`, `other` | guardian_bindings.relation |
| parse_status | `pending`, `parsing`, `completed`, `failed` | textbooks.parse_status |
| difficulty | `basic`, `intermediate`, `advanced` | knowledge_points, generated_resources |
| review_status | `auto`, `reviewed`/`approved`, `rejected` | knowledge_points, generated_resources |
| resource_type | `game_quiz`, `game_drag_match`, `video_script`, `practice_set` | generated_resources, learning_records |
| task_type | `after_class`, `review`, `assessment` | tasks.task_type |
| task_status | `draft`, `published`, `archived` | tasks.status |
| learning_status | `started`, `in_progress`, `completed`, `abandoned` | learning_records.status |
| progress_status | `not_started`, `in_progress`, `completed` | task_progress.overall_status |
| question_type | `single_choice`, `multi_choice`, `fill_blank`, `true_false` | practice_set content |

---

## 9. 数据库 Schema 隔离

每个服务使用独立 PostgreSQL schema，首期共用一个数据库实例：

```sql
CREATE SCHEMA IF NOT EXISTS user_profile;
CREATE SCHEMA IF NOT EXISTS content_engine;
CREATE SCHEMA IF NOT EXISTS media_generation;
CREATE SCHEMA IF NOT EXISTS learning_orchestrator;
CREATE SCHEMA IF NOT EXISTS analytics_reporting;
```

各服务只访问自己的 schema。跨服务数据通过 API 调用或事件消费获取，**禁止跨 schema 直接 JOIN**。
