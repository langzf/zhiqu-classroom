/** 学习任务类型 */
export type TaskType = 'practice' | 'review' | 'preview' | 'test' | 'custom';

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  practice: '练习',
  review: '复习',
  preview: '预习',
  test: '测验',
  custom: '自定义',
};

/** 任务项状态 */
export type TaskItemStatus = 'pending' | 'in_progress' | 'completed' | 'skipped';

export const TASK_ITEM_STATUS_LABELS: Record<TaskItemStatus, string> = {
  pending: '待完成',
  in_progress: '进行中',
  completed: '已完成',
  skipped: '已跳过',
};

/** 学习任务 (后端 TaskOut) */
export interface LearningTask {
  id: string;
  student_id: string;
  title: string;
  task_type: TaskType;
  status: string;
  config_json: Record<string, unknown> | null;
  progress_pct: number;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  item_count?: number;
}

/** 任务项 (后端 TaskItemOut) */
export interface TaskItem {
  id: string;
  task_id: string;
  knowledge_point_id: string | null;
  resource_id: string | null;
  seq: number;
  status: TaskItemStatus;
  score: number | null;
  answer_json: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
}

/** 任务进度 */
export interface TaskProgress {
  id: string;
  task_id: string;
  student_id: string;
  progress_pct: number;
  score: number | null;
  started_at: string | null;
  completed_at: string | null;
}

/** 学习记录 */
export interface LearningRecord {
  id: string;
  task_id: string;
  student_id: string;
  score: number | null;
  answer_json: Record<string, unknown> | null;
  duration_seconds: number | null;
  created_at: string;
}

/** 提交进度请求 */
export interface SubmitProgressRequest {
  status: TaskItemStatus;
  score?: number;
  answer_json?: Record<string, unknown>;
  duration_seconds?: number;
}
