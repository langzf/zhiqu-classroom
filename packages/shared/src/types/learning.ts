/** 学习任务 */
export interface LearningTask {
  id: string;
  title: string;
  description: string | null;
  student_id: string;
  knowledge_point_ids: string[];
  status: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
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
