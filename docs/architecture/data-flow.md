# 核心业务流程与数据流转

> 端到端业务场景的数据流、服务交互与状态变迁

---

## 1. 教材上传与解析

> 管理员上传教材 → 系统自动解析 → 知识点就绪 → 可生成教学内容

```
管理员                content-engine             Doc Parser          LLM Gateway
  │                        │                        │                    │
  │──POST /textbooks──────►│                        │                    │
  │  (file + metadata)     │                        │                    │
  │                        │──存储文件──►MinIO       │                    │
  │                        │──写入textbooks表────►PG  │                    │
  │◄──202 Accepted─────────│  (parse_status=pending) │                    │
  │                        │                        │                    │
  │                        │──publish──►stream:textbook.uploaded          │
  │                        │                        │                    │
  │               Worker 消费事件                    │                    │
  │                        │──PDF/DOCX──────────────►│                    │
  │                        │◄──结构化文本────────────│                    │
  │                        │                        │                    │
  │                        │──知识点抽取 prompt──────────────────────────►│
  │                        │◄──知识点 JSON──────────────────────────────│
  │                        │                        │                    │
  │                        │──向量化──►Embedding Svc  │                    │
  │                        │──写入 chapters, knowledge_points, kp_embeddings
  │                        │──parse_status=completed  │                    │
  │                        │──publish──►stream:textbook.parsed            │
```

**状态流转：**
```
textbook.parse_status:
  pending → parsing → completed
                    → failed (可重试)
```

---

## 2. 互动内容生成

> 知识点就绪 → 自动/手动触发生成 → 游戏/视频/练习 → 质量审核 → 可用

```
textbook.parsed 事件           media-generation              LLM Gateway
        │                           │                            │
        │──consume────────────────►│                            │
        │                           │                            │
        │                           │──查询知识点详情──►content-engine
        │                           │◄──知识点列表──────────────│
        │                           │                            │
        │                           │──加载 prompt_template      │
        │                           │──渲染模板(Jinja2)          │
        │                           │──调用 LLM──────────────────►│
        │                           │◄──生成内容 JSON────────────│
        │                           │                            │
        │                           │──JSON Schema 校验          │
        │                           │──质量评审(可选 LLM 二审)   │
        │                           │──写入 generated_resources  │
        │                           │  (review_status=auto_approved / pending_review)
        │                           │                            │
        │                           │──publish──►stream:resource.generated
```

**生成类型与触发：**

| 类型 | 触发方式 | 典型耗时 |
|------|----------|----------|
| `game_interactive` | 教材解析完成自动触发 | 30-60s |
| `video_script` | 管理员手动触发 | 20-45s |
| `practice_set` | 教材解析完成自动触发 | 15-30s |

**质量控制：**
```
review_status:
  auto_approved   → quality_score ≥ 0.8，自动通过
  pending_review  → quality_score < 0.8，等待人工审核
  approved        → 人工审核通过
  rejected        → 人工审核拒绝，需重新生成
```

---

## 3. 学习任务流转

> 资源就绪 → 创建任务 → 分配学生 → 学生执行 → 完成统计

```
管理员/系统            learning-orchestrator        学生端
    │                        │                       │
    │──POST /tasks──────────►│                       │
    │  (resource_ids,        │──写入 tasks 表         │
    │   chapter_id,          │  status=draft         │
    │   task_type)           │                       │
    │                        │                       │
    │──POST /tasks/:id/      │                       │
    │  assign               │                       │
    │  (assign_type=class,  │──写入 task_assignments │
    │   target_id=class_1)  │  progress=0            │
    │                        │                       │
    │──PATCH /tasks/:id      │                       │
    │  status=published     │──通知学生──────────────►│
    │                        │                       │
    │                        │     学生查看任务列表    │
    │                        │◄──GET /my/tasks───────│
    │                        │──任务列表──────────────►│
    │                        │                       │
    │                        │     学生执行任务        │
    │                        │◄──POST /learning-     │
    │                        │   records             │
    │                        │  (action: start/      │
    │                        │   answer/complete)    │
    │                        │                       │
    │                        │──更新 progress         │
    │                        │──完成时:               │
    │                        │  completed_at=now     │
    │                        │  score=计算结果        │
    │                        │                       │
    │                        │──publish──►stream:task.completed
```

**任务状态：**
```
task.status:      draft → published → archived
assignment.status: assigned → in_progress → completed → expired
```

---

## 4. AI 辅导对话

> 学生提问 → RAG 检索 → LLM 生成 → 流式响应

```
学生端                 ai-tutor              RAG Pipeline         LLM Gateway
  │                      │                       │                    │
  │──POST /conversations │                       │                    │
  │  (subject, chapter)  │──创建对话记录          │                    │
  │◄──conversation_id────│                       │                    │
  │                      │                       │                    │
  │──POST /conversations/│                       │                    │
  │  :id/messages        │                       │                    │
  │  "什么是勾股定理？"    │                       │                    │
  │                      │──加载最近N条消息        │                    │
  │                      │                       │                    │
  │                      │──检索相关知识──────────►│                    │
  │                      │                       │──向量检索(pgvector) │
  │                      │                       │──重排序             │
  │                      │◄──Top-K 知识片段───────│                    │
  │                      │                       │                    │
  │                      │──组装 System Prompt     │                    │
  │                      │  + 知识上下文           │                    │
  │                      │  + 对话历史             │                    │
  │                      │──流式调用 LLM──────────────────────────────►│
  │                      │◄──SSE token stream──────────────────────────│
  │◄──SSE: 勾股定理是...──│                       │                    │
  │◄──SSE: 在直角三角...──│                       │                    │
  │◄──SSE: [DONE]────────│                       │                    │
  │                      │──保存 assistant 消息    │                    │
  │                      │──异步更新对话摘要       │                    │
```

**对话策略：**
- System Prompt 角色设定：苏格拉底式教师，引导思考而非直接给答案
- 上下文窗口：最近 20 条消息 + RAG 检索结果，总 token 不超过 4096
- 流式输出：SSE（Server-Sent Events），每个 token 即时推送
- 超时处理：120s 无响应自动断开

---

## 5. 统计报表生成

> 学习数据 → 每日聚合 → 周报生成 → 推送家长

```
定时任务(cron)         analytics-reporting         LLM Gateway        notification
    │                        │                        │                    │
    │ 每日 02:00             │                        │                    │
    │──触发日统计────────────►│                        │                    │
    │                        │──聚合 learning_records  │                    │
    │                        │  → daily_study_stats   │                    │
    │                        │  (per student per day) │                    │
    │                        │                        │                    │
    │ 每周日 03:00            │                        │                    │
    │──触发周报生成──────────►│                        │                    │
    │                        │──汇总本周数据           │                    │
    │                        │──生成报告 JSON          │                    │
    │                        │                        │                    │
    │                        │──请求个性化评语─────────►│                    │
    │                        │◄──AI 评语──────────────│                    │
    │                        │                        │                    │
    │                        │──写入 weekly_reports    │                    │
    │                        │──publish──►stream:report.ready             │
    │                        │                        │                    │
    │                        │                        │      consume事件   │
    │                        │                        │            ────────►│
    │                        │                        │                    │
    │                        │                        │  查找家长绑定关系   │
    │                        │                        │  渲染通知模板       │
    │                        │                        │  推送微信/短信      │
```

**聚合维度：**

| 指标 | 粒度 | 来源 |
|------|------|------|
| `study_duration_min` | 每日/每周 | learning_records (start/end 时间差) |
| `tasks_completed` | 每日/每周 | task_assignments (completed_at 非空) |
| `accuracy_rate` | 每日/每周 | learning_records (correct/total) |
| `knowledge_mastery` | 累计 | 知识点维度正确率加权 |
| `active_days` | 每周 | 有学习记录的天数 |

---

## 6. 端到端全景：从教材到学习报告

```
                        zhiqu-classroom 全景数据流
                        ═══════════════════════════

  ┌─────────┐     ┌──────────────┐     ┌───────────────┐
  │ 管理员   │────►│ 上传教材 PDF  │────►│ 文档解析+OCR  │
  └─────────┘     └──────────────┘     └───────┬───────┘
                                               │
                                               ▼
                                      ┌───────────────┐
                                      │ 知识点抽取     │
                                      │ (LLM + 向量化) │
                                      └───────┬───────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         ▼                     ▼                     ▼
                  ┌─────────────┐     ┌───────────────┐     ┌─────────────┐
                  │ 游戏生成     │     │ 视频脚本生成   │     │ 练习题生成   │
                  │ (LLM)       │     │ (LLM)         │     │ (LLM)       │
                  └──────┬──────┘     └───────┬───────┘     └──────┬──────┘
                         │                    │                     │
                         └─────────┬──────────┘─────────────────────┘
                                   ▼
                          ┌───────────────┐
                          │ 创建学习任务   │
                          │ 分配给学生     │
                          └───────┬───────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │          学生学习              │
                  │  ┌────────┐ ┌──────┐ ┌──────┐ │
                  │  │ 做游戏  │ │看视频 │ │做练习 │ │
                  │  └────────┘ └──────┘ └──────┘ │
                  │        ↕ AI 辅导对话           │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │ 学习数据采集   │
                          │ 行为记录流水   │
                          └───────┬───────┘
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
                  ┌─────────────┐   ┌─────────────┐
                  │ 每日统计     │   │ 周报生成     │
                  │ 知识掌握度   │   │ AI 个性化    │
                  └─────────────┘   └──────┬──────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │ 推送家长     │
                                   │ 微信/短信    │
                                   └─────────────┘
```