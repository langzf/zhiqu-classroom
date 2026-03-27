# 学习引擎域数据模型

> 对应服务：`learning-orchestrator`
> Schema 隔离：`learning`

---

## 概述

学习引擎域管理学习任务的全生命周期：任务创建 → 分配 → 学习记录 → 进度追踪。是连接课程内容与学习分析的核心桥梁。

### 表清单

| 表名 | 说明 | 预估行数 |
|------|------|----------|
| `tasks` | 学习任务主表 | 万级 |
| `task_assignments` | 任务分配 | 十万级 |
| `task_progress` | 任务进度 | 十万级 |
| `learning_records` | 学习行为流水 | 百万级 |

---

## 1. tasks — 学习任务

```sql
CREATE TABLE tasks (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                 VARCHAR(200) NOT NULL,
    task_type             VARCHAR(30)  NOT NULL,       -- after_class / review / assessment
    description           TEXT,
    textbook_id           UUID,                        -- ref: textbooks.id
    chapter_id            UUID,                        -- ref: chapters.id
    knowledge_points      JSONB        NOT NULL DEFAULT '[]',
                                                       -- 关联知识点 UUID 列表
    resource_ids          JSONB        NOT NULL DEFAULT '[]',
                                                       -- 关联资源 UUID 列表
    difficulty            VARCHAR(20)  NOT NULL DEFAULT 'basic',
    estimated_duration_min INT,                        -- 预估时长（分钟）
    status                VARCHAR(20)  NOT NULL DEFAULT 'draft',
                                                       -- draft / published / archived
    config                JSONB        NOT NULL DEFAULT '{}',
                                                       -- 任务配置（截止时间、允许重做等）
    created_by            UUID         NOT NULL,        -- ref: users.id（教师）
    is_active             BOOLEAN      NOT NULL DEFAULT true,
    version               INT          NOT NULL DEFAULT 1,
    deleted_at            TIMESTAMP,
    created_at            TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at            TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_tasks_textbook ON tasks(textbook_id);
CREATE INDEX idx_tasks_status   ON tasks(status);
CREATE INDEX idx_tasks_type     ON tasks(task_type);
CREATE INDEX idx_tasks_creator  ON tasks(created_by);
```

### task_type 枚举

| 值 | 说明 |
|------|------|
| `after_class` | 课后作业 |
| `review` | 复习任务 |
| `assessment` | 评测任务 |

### config JSONB Schema

```json
{
  "deadline": "2024-03-20T23:59:59+08:00",
  "allow_retry": true,
  "max_attempts": 3,
  "passing_score": 60,
  "show_answer_after_submit": true,
  "randomize_questions": false
}
```

---

## 2. task_assignments — 任务分配

```sql
CREATE TABLE task_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID         NOT NULL,           -- ref: tasks.id
    student_id      UUID         NOT NULL,           -- ref: users.id
    assign_type     VARCHAR(20)  NOT NULL,            -- individual / class / grade
    assign_target   VARCHAR(100),                    -- 分配目标标识（班级ID/年级）
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
                                                     -- pending / in_progress / completed / overdue
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    score           DECIMAL(5,2),                    -- 得分
    attempt_count   INT          NOT NULL DEFAULT 0,
    result          JSONB        NOT NULL DEFAULT '{}',
                                                     -- 结果详情
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX idx_ta_task    ON task_assignments(task_id);
CREATE INDEX idx_ta_student ON task_assignments(student_id);
CREATE INDEX idx_ta_status  ON task_assignments(status);
CREATE UNIQUE INDEX uniq_ta ON task_assignments(task_id, student_id);
```

### status 流转

```
pending → in_progress → completed
                     ↘ overdue（超过截止时间未完成）
```

### result JSONB Schema

```json
{
  "answers": [
    {
      "question_id": "uuid-...",
      "student_answer": "B",
      "is_correct": false,
      "score": 0,
      "time_spent_sec": 45
    }
  ],
  "total_score": 75,
  "total_time_sec": 1200,
  "accuracy_rate": 0.75
}
```

---

## 3. task_progress — 任务进度

```sql
CREATE TABLE task_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id   UUID         NOT NULL,           -- ref: task_assignments.id
    student_id      UUID         NOT NULL,           -- ref: users.id
    progress_pct    INT          NOT NULL DEFAULT 0, -- 完成百分比 0-100
    current_step    VARCHAR(100),                    -- 当前步骤标识
    step_data       JSONB        NOT NULL DEFAULT '{}',
                                                     -- 步骤状态快照
    last_active_at  TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX uniq_tp_assignment ON task_progress(assignment_id);
CREATE INDEX idx_tp_student ON task_progress(student_id);
```

### step_data JSONB Schema

```json
{
  "completed_items": ["q1", "q2", "q3"],
  "total_items": 10,
  "bookmarks": ["q5"],
  "time_per_item": {
    "q1": 30,
    "q2": 45,
    "q3": 60
  }
}
```

---

## 4. learning_records — 学习行为流水

```sql
CREATE TABLE learning_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID         NOT NULL,           -- ref: users.id
    assignment_id   UUID,                            -- ref: task_assignments.id（可选）
    resource_id     UUID,                            -- ref: generated_resources.id（可选）
    event_type      VARCHAR(50)  NOT NULL,            -- 事件类型
    event_data      JSONB        NOT NULL DEFAULT '{}',
                                                     -- 事件详情
    duration_sec    INT,                             -- 持续时长（秒）
    device_info     JSONB        NOT NULL DEFAULT '{}',
                                                     -- 设备信息
    client_ts       TIMESTAMP,                       -- 客户端时间戳
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引（高写入表，索引从严控制）
CREATE INDEX idx_lr_student    ON learning_records(student_id, created_at DESC);
CREATE INDEX idx_lr_assignment ON learning_records(assignment_id)
    WHERE assignment_id IS NOT NULL;
CREATE INDEX idx_lr_event_type ON learning_records(event_type, created_at DESC);
```

### event_type 枚举

| 值 | 说明 |
|------|------|
| `task_start` | 开始任务 |
| `task_submit` | 提交任务 |
| `question_answer` | 回答题目 |
| `resource_view` | 查看资源 |
| `game_play` | 玩游戏 |
| `game_complete` | 完成游戏 |
| `video_watch` | 观看视频 |
| `hint_request` | 请求提示 |
| `page_stay` | 页面停留 |

### event_data 示例

**question_answer**
```json
{
  "question_id": "uuid-...",
  "answer": "B",
  "is_correct": true,
  "time_spent_sec": 30,
  "attempt_no": 1
}
```

**game_complete**
```json
{
  "game_id": "uuid-...",
  "score": 85,
  "max_score": 100,
  "time_spent_sec": 180,
  "mistakes": 2
}
```

### device_info JSONB Schema

```json
{
  "platform": "ios | android | web",
  "app_version": "1.2.0",
  "os_version": "iOS 17.4",
  "screen_size": "390x844",
  "network": "wifi"
}
```

> **分区策略**：`learning_records` 为高写入表，当数据量超过千万时，建议按 `created_at` 做月度范围分区。

---

## 关系图

```
tasks (教师创建)
└── task_assignments (student_id, task_id)
    ├── task_progress (assignment_id)
    └── learning_records (assignment_id, student_id)
```

## 常用查询

### 学生待完成任务列表

```sql
SELECT t.id, t.title, t.task_type, t.estimated_duration_min,
       ta.status, ta.attempt_count
FROM task_assignments ta
JOIN tasks t ON t.id = ta.task_id
WHERE ta.student_id = :student_id
  AND ta.status IN ('pending', 'in_progress')
  AND t.deleted_at IS NULL
ORDER BY t.created_at DESC;
```

### 任务完成率统计

```sql
SELECT t.id, t.title,
       COUNT(ta.id) AS total_assigned,
       COUNT(ta.id) FILTER (WHERE ta.status = 'completed') AS completed,
       ROUND(
           COUNT(ta.id) FILTER (WHERE ta.status = 'completed')::numeric
           / NULLIF(COUNT(ta.id), 0) * 100, 1
       ) AS completion_pct
FROM tasks t
JOIN task_assignments ta ON ta.task_id = t.id
WHERE t.created_by = :teacher_id
GROUP BY t.id, t.title;
```

### 学生近期学习行为

```sql
SELECT event_type, event_data, duration_sec, created_at
FROM learning_records
WHERE student_id = :student_id
  AND created_at >= now() - interval '7 days'
ORDER BY created_at DESC
LIMIT 50;
```
