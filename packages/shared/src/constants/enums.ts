// ── Roles ──
export const ROLES = ['student', 'guardian', 'admin', 'teacher'] as const;
export type UserRole = (typeof ROLES)[number];

// ── Subjects ──
export const SUBJECTS = [
  'math', 'chinese', 'english', 'physics',
  'chemistry', 'biology', 'history', 'geography', 'politics',
] as const;
export type Subject = (typeof SUBJECTS)[number];

export const SUBJECT_LABELS: Record<Subject, string> = {
  math: '数学', chinese: '语文', english: '英语',
  physics: '物理', chemistry: '化学', biology: '生物',
  history: '历史', geography: '地理', politics: '政治',
};

// ── Grades ──
export const GRADES = [
  'grade_1', 'grade_2', 'grade_3', 'grade_4', 'grade_5', 'grade_6',
  'grade_7', 'grade_8', 'grade_9', 'grade_10', 'grade_11', 'grade_12',
] as const;
export type Grade = (typeof GRADES)[number];

export const GRADE_LABELS: Record<Grade, string> = {
  grade_1: '一年级', grade_2: '二年级', grade_3: '三年级',
  grade_4: '四年级', grade_5: '五年级', grade_6: '六年级',
  grade_7: '初一', grade_8: '初二', grade_9: '初三',
  grade_10: '高一', grade_11: '高二', grade_12: '高三',
};

// ── Parse Status ──
export const PARSE_STATUSES = ['pending', 'parsing', 'completed', 'failed'] as const;
export type ParseStatus = (typeof PARSE_STATUSES)[number];

export const PARSE_STATUS_LABELS: Record<ParseStatus, string> = {
  pending: '待解析', parsing: '解析中', completed: '已完成', failed: '失败',
};

// ── Task Status ──
export const TASK_STATUSES = ['draft', 'active', 'expired', 'archived'] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: '草稿', active: '进行中', expired: '已过期', archived: '已归档',
};

// ── Exercise Types ──
export const EXERCISE_TYPES = ['choice', 'fill_blank', 'short_answer', 'true_false'] as const;
export type ExerciseType = (typeof EXERCISE_TYPES)[number];
