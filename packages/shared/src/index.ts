// ── Types ──
export type { ApiResponse, PaginatedData, PaginatedResponse, ApiError } from './types/api';
export type { UserInfo, StudentProfile, TokenOut, LoginRequest, RegisterRequest, User } from './types/user';
export type { Textbook, Chapter, KnowledgePoint, GeneratedResource } from './types/content';
export type { Conversation, ConversationScene, Message, SendMessageResponse, FeedbackRequest } from './types/tutor';
export { SCENE_LABELS } from './types/tutor';
export type { LearningTask, TaskItem, TaskItemStatus, TaskType, LearningTaskType, TaskProgress, LearningRecord, SubmitProgressRequest } from './types/learning';
export { TASK_TYPE_LABELS, LEARNING_TASK_TYPE_LABELS, TASK_ITEM_STATUS_LABELS } from './types/learning';

// ── Constants ──
export {
  SUBJECTS, GRADES, ROLES, PARSE_STATUSES, TASK_STATUSES, LEARNING_TASK_STATUSES, EXERCISE_TYPES,
  SUBJECT_LABELS, GRADE_LABELS, PARSE_STATUS_LABELS, TASK_STATUS_LABELS,
  LEARNING_TASK_STATUS_LABELS, EXERCISE_TYPE_LABELS, ROLE_LABELS,
} from './constants/enums';
export type { UserRole, Subject, Grade, ParseStatus, TaskStatus, LearningTaskStatus, ExerciseType } from './constants/enums';
export { ERROR_CODES } from './constants/errors';

// ── Utils ──
export { formatDate, formatDuration, formatNumber } from './utils/format';
export { isValidPhone, isValidCode } from './utils/validate';
