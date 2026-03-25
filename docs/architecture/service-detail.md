# 服务详细设计

> 各服务职责、边界、核心接口与依赖关系

---

## 1. user-profile（用户管理）

### 职责
- 手机号验证码登录 / 微信登录
- JWT 签发与刷新
- 用户信息管理（昵称、头像、学校、年级）
- 学生档案（学习偏好、当前教材绑定）
- 家长-学生绑定关系

### 数据模型
- `users` — 用户主表（phone, wx_openid, role, avatar_url）
- `student_profiles` — 学生扩展信息（school, grade, learning_preference）
- `guardian_bindings` — 家长绑定关系（guardian_id → student_id）

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/sms/send` | 发送短信验证码 |
| POST | `/auth/sms/verify` | 验证码登录 |
| POST | `/auth/wx/login` | 微信登录 |
| POST | `/auth/token/refresh` | 刷新 Token |
| GET | `/users/me` | 获取当前用户信息 |
| PATCH | `/users/me` | 更新用户信息 |
| GET/PATCH | `/users/me/student-profile` | 学生档案 |
| POST | `/users/me/guardian-bindlings` | 绑定家长 |

### 依赖
- **Redis** — 验证码存储（5分钟TTL）、Token 黑名单、登录频率限制
- **PostgreSQL** — 用户数据持久化
- 被其他所有服务依赖（通过 user_id 引用）

### 边界规则
- 不处理任何业务逻辑（学习、内容等）
- 其他服务只存 `user_id: UUID`，不冗余用户字段
- 当其他服务需要用户信息时通过内部接口查询（MVP 同进程直接调用）

---

## 2. content-engine（内容引擎）

### 职责
- 教材 PDF/DOCX 上传与解析
- 章节结构提取（目录树）
- 知识点抽取（LLM 辅助）
- 知识点向量化与索引（pgvector）
- 为 RAG 检索提供知识库

### 数据模型
- `textbooks` — 教材主表（subject, grade_range, file_url, parse_status）
- `chapters` — 章节树（parent_id 自引用，深度不超过 4 层）
- `knowledge_points` — 知识点（关联 chapter_id，difficulty, tags JSONB）
- `kp_embeddings` — 知识点向量（embedding VECTOR(1024)，pgvector 索引）

### 核心流程

```
教材上传 ──► 文件存储(MinIO) ──► 发布事件 textbook.uploaded
                                        │
                                        ▼
                            Worker: 文档解析流水线
                            ├── 1. PDF/DOCX → 结构化文本（Doc Parser）
                            ├── 2. 目录树 → chapters 表
                            ├── 3. 内容 → 知识点抽取（LLM）
                            ├── 4. 知识点 → 向量化（Embedding）
                            ├── 5. 更新 parse_status = completed
                            └── 6. 发布事件 textbook.parsed
```

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/textbooks` | 创建教材 + 上传文件 |
| GET | `/textbooks` | 教材列表（支持按学科/年级筛选） |
| GET | `/textbooks/:id` | 教材详情（含解析状态） |
| GET | `/textbooks/:id/chapters` | 获取章节树 |
| POST | `/textbooks/:id/parse` | 触发重新解析 |
| GET | `/chapters/:id/knowledge-points` | 章节下知识点列表 |
| GET | `/knowledge-points/:id` | 知识点详情 |
| POST | `/knowledge-points/search` | 向量语义搜索 |

### 依赖
- **MinIO/OSS** — 教材文件存储
- **LLM Gateway** — 知识点抽取、结构化
- **Embedding Service** — 知识点向量化
- **Doc Parser** — PDF/DOCX 文本提取
- **Redis Streams** — 异步解析任务

---

## 3. media-generation（内容生成）

### 职责
- 互动游戏生成（基于知识点 + 游戏模板）
- 短视频脚本生成（含分镜、旁白、字幕）
- 练习题生成（选择题、填空题、判断题等）
- Prompt 模板管理（Jinja2 渲染）
- 生成质量审核（LLM 二次校验）

### 数据模型
- `prompt_templates` — Prompt 模板（template_key, content_template Jinja2, variables JSONB）
- `generated_resources` — 生成结果（resource_type, content JSONB, quality_score, review_status）

### 核心流程

```
知识点就绪 ──► 选择生成类型（game/video/practice）
                │
                ├── 1. 查找匹配的 Prompt 模板
                ├── 2. 填充模板变量（知识点、难度、年级等）
                ├── 3. 调用 LLM 生成内容
                ├── 4. 结构化校验（JSON Schema）
                ├── 5. 质量评审（可选 LLM 二审）
                ├── 6. 存储生成结果
                └── 7. 发布事件 resource.generated
```

### resource_type 与 content JSONB 结构

| resource_type | content 结构 |
|---------------|-------------|
| `game_interactive` | `{ "game_type", "scenes": [...], "rules", "scoring" }` |
| `video_script` | `{ "title", "scenes": [{"narration", "visual", "duration"}], "total_duration" }` |
| `practice_set` | `{ "questions": [{"type", "stem", "options", "answer", "explanation"}] }` |

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/games/generate` | 生成互动游戏 |
| POST | `/videos/generate` | 生成视频脚本 |
| POST | `/practices/generate` | 生成练习题 |
| GET | `/resources/:id` | 获取生成结果 |
| GET | `/resources/:id/status` | 查询生成进度 |
| POST | `/resources/:id/review` | 人工审核 |
| GET/POST | `/prompt-templates` | 模板管理（admin） |

### 依赖
- **LLM Gateway** — 内容生成的核心依赖
- **content-engine** — 获取知识点详情
- **Redis Streams** — 异步生成任务队列
- **MinIO/OSS** — 存储多媒体素材

---

## 4. learning-orchestrator（学习编排）

### 职责
- 学习任务创建（课后任务、复习任务、测评任务）
- 任务分配（个人/班级/年级）
- 学习进度跟踪
- 学习记录流水（操作粒度的行为日志）
- 任务完成统计

### 数据模型
- `tasks` — 任务主表（task_type, textbook_id, chapter_id, resource_ids JSONB, status）
- `task_assignments` — 任务分配（task_id → student_id, assign_type, progress, score）
- `learning_records` — 学习行为流水（student_id, task_id, action_type, detail JSONB）
- `task_progress` — 任务进度快照（完成率、耗时、得分）

### 核心流程

```
资源就绪 ──► 创建任务（选择资源、设定参数）
              │
              ├── 分配任务 → task_assignments
              │     ├── individual: 指定学生
              │     ├── class: 班级全员
              │     └── grade: 年级全员
              │
              ├── 学生执行任务
              │     ├── 记录 learning_records（每个操作）
              │     ├── 更新 task_assignments.progress
              │     └── 完成时更新 completed_at + score
              │
              └── 发布事件 task.completed
```

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks` | 创建任务 |
| GET | `/tasks` | 任务列表（按状态/类型筛选） |
| GET | `/tasks/:id` | 任务详情 |
| PATCH | `/tasks/:id` | 更新任务（修改/发布/归档） |
| POST | `/tasks/:id/assign` | 分配任务 |
| GET | `/tasks/:id/assignments` | 查看分配列表 |
| GET | `/my/tasks` | 学生我的任务列表 |
| POST | `/learning-records` | 提交学习记录 |
| GET | `/my/learning-records` | 查看我的学习记录 |

### 依赖
- **content-engine** — 获取章节/知识点信息
- **media-generation** — 引用生成的资源 ID
- **Redis** — 任务状态缓存、进度实时更新
- **Redis Streams** — 任务完成事件

---

## 5. ai-tutor（AI 辅导）

### 职责
- 一对一 AI 辅导对话
- 多轮对话上下文管理
- 基于 RAG 的知识问答（结合教材知识点）
- 苏格拉底式引导提问（不直接给答案）
- 对话历史记录与回顾

### 数据模型
- `conversations` — 对话主表（student_id, subject, chapter_id, summary）
- `messages` — 消息记录（conversation_id, role, content, token_count）

### 核心流程

```
学生提问
  │
  ├── 1. 加载对话上下文（最近 N 条消息）
  ├── 2. RAG 检索相关知识点
  │     ├── Query 改写（LLM）
  │     ├── 向量检索（pgvector）
  │     └── 重排序 + 截断
  ├── 3. 组装 System Prompt
  │     ├── 角色设定（苏格拉底式教师）
  │     ├── 学生画像（年级、偏好）
  │     └── 检索到的知识点上下文
  ├── 4. 调用 LLM（流式输出 SSE）
  ├── 5. 保存消息记录
  └── 6. 异步更新对话摘要
```

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/conversations` | 创建新对话 |
| GET | `/conversations` | 对话列表 |
| GET | `/conversations/:id` | 对话详情 + 消息历史 |
| POST | `/conversations/:id/messages` | 发送消息（SSE 流式响应） |
| DELETE | `/conversations/:id` | 删除对话 |

### 依赖
- **LLM Gateway** — 对话生成（需支持流式）
- **RAG Pipeline** — 知识检索
- **content-engine** — 知识点数据源
- **user-profile** — 学生画像

---

## 6. analytics-reporting（统计报表）

### 职责
- 每日学习统计汇总
- 周报/月报生成（可含 LLM 个性化评语）
- 知识点掌握度分析
- 班级/年级排名与对比
- 内容使用效果分析
- 家长端学习报告推送

### 数据模型
- `daily_study_stats` — 每日学习统计（study_duration_min, tasks_completed, accuracy_rate）
- `weekly_reports` — 周报（report_data JSONB, ai_comment）
- `content_usage_stats` — 内容使用效果（resource_id, view_count, completion_rate, avg_score）

### 核心流程

```
定时任务（每日 02:00）
  │
  ├── 聚合 learning_records → daily_study_stats
  │
  └── 每周日额外执行：
        ├── 汇总本周 daily_study_stats → weekly_reports
        ├── LLM 生成个性化评语
        ├── 发布事件 report.ready
        └── notification 推送至家长
```

### 对外接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/stats/daily` | 每日学习统计 |
| GET | `/stats/weekly` | 周统计趋势 |
| GET | `/stats/knowledge-mastery` | 知识点掌握度 |
| GET | `/reports` | 周报列表 |
| GET | `/reports/:id` | 周报详情 |
| GET | `/stats/class/:id` | 班级统计（admin） |
| GET | `/stats/content-usage` | 内容效果分析（admin） |

### 依赖
- **learning-orchestrator** — 消费 task.completed 事件
- **LLM Gateway** — 生成个性化评语
- **Redis** — 聚合结果缓存
- **notification** — 报告推送

---

## 7. notification（消息触达）

### 职责
- 短信通知（验证码、重要提醒）
- 微信服务号 / 小程序模板消息
- 站内消息
- 消息模板管理
- 发送记录与送达状态跟踪

### 数据模型
- `notification_templates` — 消息模板（channel, template_code, content_template）
- `notification_logs` — 发送记录（user_id, channel, status, sent_at, error_message）

### 核心流程

```
事件到达（report.ready / system.alert / ...）
  │
  ├── 1. 查找目标用户（学生/家长）
  ├── 2. 选择通知渠道（偏好 or 规则）
  ├── 3. 渲染消息模板
  ├── 4. 调用渠道 SDK 发送
  │     ├── SMS → 阿里云短信 / 腾讯云短信
  │     ├── 微信 → 模板消息 API
  │     └── 站内 → 写入 notification_logs
  └── 5. 记录发送结果
```

### 对外接口

主要通过事件驱动触发，不直接暴露给客户端。管理端可查看发送记录：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/notifications/logs` | 发送记录列表 |
| GET | `/admin/notifications/templates` | 模板管理 |

### 依赖
- **Redis Streams** — 消费通知事件
- **第三方 SMS SDK** — 短信发送
- **微信 API** — 模板消息

---

## 8. 服务依赖关系

```
                    ┌──────────────┐
                    │ api-gateway  │
                    │  路由/认证    │
                    └──────┬───────┘
                           │
       ┌───────────────────┼───────────────────────┐
       │                   │                       │
       ▼                   ▼                       ▼
┌─────────────┐   ┌───────────────┐   ┌──────────────────────┐
│user-profile │   │content-engine │   │learning-orchestrator │
│  用户管理    │   │  教材知识点    │   │    任务编排           │
└──────┬──────┘   └───────┬───────┘   └──────────┬───────────┘
       │                  │                      │
       │          ┌───────┴───────┐              │
       │          ▼               ▼              │
       │   ┌────────────┐ ┌──────────┐          │
       │   │media-gen   │ │ai-tutor  │          │
       │   │ 内容生成    │ │ AI辅导   │          │
       │   └─────┬──────┘ └────┬─────┘          │
       │         │             │                 │
       │         └──────┬──────┘                 │
       │                ▼                        │
       │        ┌──────────────┐                 │
       │        │ LLM Gateway  │                 │
       │        │  模型路由     │                 │
       │        └──────────────┘                 │
       │                                         │
       │         ┌──────────────────────┐        │
       └────────►│ analytics-reporting  │◄───────┘
                 │   统计报表            │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    notification      │
                 │     消息触达          │
                 └──────────────────────┘
```

**依赖规则：**
- 箭头方向 = 调用/依赖方向
- `user-profile` 是全局被依赖的基础服务
- `content-engine` 是 AI 相关服务的数据源
- `analytics-reporting` 是数据汇聚点（只消费，不被业务依赖）
- `notification` 是终端输出（只发送，不被业务依赖）
- 禁止循环依赖：A→B 且 B→A 不允许，改用事件解耦