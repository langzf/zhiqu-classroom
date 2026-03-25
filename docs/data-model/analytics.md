# 学习分析域数据模型

> 对应服务：`analytics-reporting`
> Schema 隔离：`analytics`

---

## 概述

学习分析域负责聚合学习行为数据，生成统计报表和学习洞察。采用预聚合策略减少实时计算压力，为家长端报告、教师看板提供数据支撑。

### 表清单

| 表名 | 说明 | 预估行数 |
|------|------|----------|
| `daily_study_stats` | 每日学习统计 | 百万级 |
| `weekly_reports` | 每周学习报告 | 十万级 |
| `content_usage_stats` | 内容使用统计 | 万级 |

---

## 1. daily_study_stats — 每日学习统计

```sql
CREATE TABLE daily_study_stats (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID         NOT NULL,           -- ref: users.id
    stat_date       DATE         NOT NULL,           -- 统计日期
    total_duration_min INT       NOT NULL DEFAULT 0, -- 总学习时长（分钟）
    task_completed  INT          NOT NULL DEFAULT 0, -- 完成任务数
    task_attempted  INT          NOT NULL DEFAULT 0, -- 尝试任务数
    questions_answered INT       NOT NULL DEFAULT 0, -- 回答题目数
    correct_count   INT          NOT NULL DEFAULT 0, -- 正确数
    games_played    INT          NOT NULL DEFAULT 0, -- 游戏次数
    resources_viewed INT         NOT NULL DEFAULT 0, -- 查看资源数
    ai_conversations INT         NOT NULL DEFAULT 0, -- AI 对话次数
    streak_days     INT          NOT NULL DEFAULT 0, -- 连续学习天数
    details         JSONB        NOT NULL DEFAULT '{}',
                                                     -- 明细数据
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX uniq_dss_student_date ON daily_study_stats(student_id, stat_date);
CREATE INDEX idx_dss_date ON daily_study_stats(stat_date);
```

### details JSONB Schema

```json
{
  "by_subject": {
    "math": { "duration_min": 30, "tasks": 2, "accuracy": 0.85 },
    "chinese": { "duration_min": 20, "tasks": 1, "accuracy": 0.90 }
  },
  "by_difficulty": {
    "basic": { "count": 10, "correct": 9 },
    "intermediate": { "count": 5, "correct": 3 },
    "advanced": { "count": 2, "correct": 1 }
  },
  "active_hours": [9, 10, 14, 15, 20, 21]
}
```

> **生成策略**：每日凌晨由定时任务从 `learning_records` 聚合生成前一天的统计数据。也支持通过实时事件流增量更新当天数据。

---

## 2. weekly_reports — 每周学习报告

```sql
CREATE TABLE weekly_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID         NOT NULL,           -- ref: users.id
    week_start      DATE         NOT NULL,           -- 周起始日（周一）
    week_end        DATE         NOT NULL,           -- 周结束日（周日）
    summary         JSONB        NOT NULL DEFAULT '{}',
                                                     -- 汇总数据
    highlights      JSONB        NOT NULL DEFAULT '[]',
                                                     -- 亮点列表
    suggestions     JSONB        NOT NULL DEFAULT '[]',
                                                     -- AI 建议列表
    knowledge_mastery JSONB      NOT NULL DEFAULT '{}',
                                                     -- 知识点掌握度
    report_text     TEXT,                            -- AI 生成的报告文本
    model_name      VARCHAR(100),                    -- 生成报告使用的模型
    llm_call_id     UUID,                            -- ref: llm_call_logs.id
    sent_to_guardian BOOLEAN     NOT NULL DEFAULT false,
    sent_at         TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX uniq_wr_student_week ON weekly_reports(student_id, week_start);
CREATE INDEX idx_wr_week ON weekly_reports(week_start);
```

### summary JSONB Schema

```json
{
  "total_duration_min": 210,
  "total_tasks": 15,
  "completed_tasks": 12,
  "avg_accuracy": 0.82,
  "total_games": 8,
  "streak_days": 5,
  "vs_last_week": {
    "duration_change_pct": 15.5,
    "accuracy_change_pct": 3.2,
    "tasks_change": 2
  }
}
```

### highlights & suggestions JSONB Schema

```json
// highlights
[
  { "type": "achievement", "text": "本周连续5天完成学习任务！" },
  { "type": "improvement", "text": "数学正确率从 75% 提升到 85%" }
]

// suggestions
[
  { "priority": "high", "text": "建议加强分数运算的练习", "knowledge_point_id": "uuid-..." },
  { "priority": "medium", "text": "可以尝试更多进阶难度的题目" }
]
```

### knowledge_mastery JSONB Schema

```json
{
  "uuid-kp-1": { "title": "一元二次方程", "mastery": 0.90, "practice_count": 15 },
  "uuid-kp-2": { "title": "分式化简", "mastery": 0.65, "practice_count": 8 },
  "uuid-kp-3": { "title": "勾股定理", "mastery": 0.45, "practice_count": 3 }
}
```

---

## 3. content_usage_stats — 内容使用统计

```sql
CREATE TABLE content_usage_stats (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id     UUID         NOT NULL,           -- ref: generated_resources.id
    stat_date       DATE         NOT NULL,
    view_count      INT          NOT NULL DEFAULT 0,
    unique_users    INT          NOT NULL DEFAULT 0,
    avg_duration_sec INT,
    completion_rate DECIMAL(5,2),                    -- 完成率百分比
    avg_score       DECIMAL(5,2),                    -- 平均得分
    feedback_positive INT        NOT NULL DEFAULT 0,
    feedback_negative INT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX uniq_cus_resource_date ON content_usage_stats(resource_id, stat_date);
CREATE INDEX idx_cus_date ON content_usage_stats(stat_date);
```

---

## 关系图

```
learning_records (源数据)
    ↓ 聚合
daily_study_stats (student_id, stat_date)
    ↓ 汇总
weekly_reports (student_id, week_start)
    → 推送给 guardian

generated_resources (源数据)
    ↓ 聚合
content_usage_stats (resource_id, stat_date)
```

## 数据生成策略

| 表 | 生成方式 | 触发时机 |
|----|---------|---------|
| `daily_study_stats` | 定时任务 + 增量更新 | 每日 02:00 全量聚合 + 实时事件增量 |
| `weekly_reports` | 定时任务 + LLM 生成 | 每周一 06:00 |
| `content_usage_stats` | 定时任务 | 每日 03:00 |

---

## 常用查询

### 学生近7天学习趋势

```sql
SELECT stat_date, total_duration_min, task_completed,
       correct_count::numeric / NULLIF(questions_answered, 0) AS accuracy
FROM daily_study_stats
WHERE student_id = :student_id
  AND stat_date >= CURRENT_DATE - 7
ORDER BY stat_date;
```

### 家长端周报

```sql
SELECT week_start, summary, highlights, suggestions,
       knowledge_mastery, report_text, sent_at
FROM weekly_reports
WHERE student_id = :student_id
ORDER BY week_start DESC
LIMIT 4;
```

### 热门资源排行

```sql
SELECT r.id, r.title, r.resource_type,
       SUM(c.view_count) AS total_views,
       AVG(c.avg_score) AS avg_score
FROM content_usage_stats c
JOIN generated_resources r ON r.id = c.resource_id
WHERE c.stat_date >= CURRENT_DATE - 30
GROUP BY r.id, r.title, r.resource_type
ORDER BY total_views DESC
LIMIT 20;
```
