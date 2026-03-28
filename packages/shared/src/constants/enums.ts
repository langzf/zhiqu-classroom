/** 用户角色 */
export type UserRole = 'student' | 'guardian' | 'admin' | 'teacher';
export const ROLES: UserRole[] = ['student', 'guardian', 'admin', 'teacher'];
export const ROLE_LABELS: Record<UserRole, string> = {
  student: '学生',
  guardian: '家长',
  admin: '管理员',
  teacher: '老师',
};

/** 学科 */
export type Subject = 'math' | 'chinese' | 'english' | 'physics' | 'chemistry' | 'biology' | 'history' | 'geography' | 'politics';
export const SUBJECTS: Subject[] = ['math', 'chinese', 'english', 'physics', 'chemistry', 'biology', 'history', 'geography', 'politics'];
export const SUBJECT_LABELS: Record<Subject, string> = {
  math: '数学',
  chinese: '语文',
  english: '英语',
  physics: '物理',
  chemistry: '化学',
  biology: '生物',
  history: '历史',
  geography: '地理',
  politics: '政治',
};

/** 年级 */
export type Grade = 'g1' | 'g2' | 'g3' | 'g4' | 'g5' | 'g6' | 'g7' | 'g8' | 'g9' | 'g10' | 'g11' | 'g12';
export const GRADES: Grade[] = ['g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12'];
export const GRADE_LABELS: Record<Grade, string> = {
  g1: '一年级', g2: '二年级', g3: '三年级',
  g4: '四年级', g5: '五年级', g6: '六年级',
  g7: '初一', g8: '初二', g9: '初三',
  g10: '高一', g11: '高二', g12: '高三',
};

/** 解析状态 */
export type ParseStatus = 'pending' | 'parsing' | 'completed' | 'failed';
export const PARSE_STATUSES: ParseStatus[] = ['pending', 'parsing', 'completed', 'failed'];
export const PARSE_STATUS_LABELS: Record<ParseStatus, string> = {
  pending: '待解析',
  parsing: '解析中',
  completed: '已完成',
  failed: '解析失败',
};

/** 任务状态 */
export type TaskStatus = 'draft' | 'published' | 'archived';
export const TASK_STATUSES: TaskStatus[] = ['draft', 'published', 'archived'];
export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档',
};

/** 练习题类型 */
export type ExerciseType = 'choice' | 'fill_blank' | 'short_answer' | 'true_false';
export const EXERCISE_TYPES: ExerciseType[] = ['choice', 'fill_blank', 'short_answer', 'true_false'];
export const EXERCISE_TYPE_LABELS: Record<ExerciseType, string> = {
  choice: '选择题',
  fill_blank: '填空题',
  short_answer: '简答题',
  true_false: '判断题',
};
