import client, { unwrap, unwrapPaged, type PagedResult } from './client';

// ── Types matching backend schemas ──

export interface TaskItem {
  id: string;
  task_id: string;
  item_type: string;
  resource_id: string | null;
  knowledge_point_id: string | null;
  title: string;
  config: Record<string, unknown> | null;
  sort_order: number;
}

export interface LearningTask {
  id: string;
  title: string;
  description: string | null;
  task_type: string;
  status: string;
  created_by: string;
  subject: string | null;
  grade_range: string | null;
  publish_at: string | null;
  deadline: string | null;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends LearningTask {
  items: TaskItem[];
}

export interface TaskProgress {
  id: string;
  task_id: string;
  student_id: string;
  status: string;
  score: number | null;
  started_at: string | null;
  completed_at: string | null;
  item_progress: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// ── Admin: Task CRUD ──

export function createTask(data: {
  title: string;
  description?: string;
  task_type?: string;
  subject?: string;
  grade_range?: string;
  publish_at?: string;
  deadline?: string;
  config?: Record<string, unknown>;
  items?: Array<{
    item_type: string;
    title: string;
    resource_id?: string;
    knowledge_point_id?: string;
    config?: Record<string, unknown>;
    sort_order?: number;
  }>;
}) {
  return unwrap<TaskDetail>(client.post('/admin/learning/tasks', data));
}

export function listTasks(params?: {
  status?: string;
  subject?: string;
  task_type?: string;
  page?: number;
  page_size?: number;
}): Promise<PagedResult<LearningTask>> {
  return unwrapPaged<LearningTask>(client.get('/admin/learning/tasks', { params }));
}

export function getTask(taskId: string) {
  return unwrap<TaskDetail>(client.get(`/admin/learning/tasks/${taskId}`));
}

export function updateTask(taskId: string, data: Partial<{
  title: string;
  description: string;
  task_type: string;
  subject: string;
  grade_range: string;
  publish_at: string;
  deadline: string;
  config: Record<string, unknown>;
  status: string;
}>) {
  return unwrap<TaskDetail>(client.patch(`/admin/learning/tasks/${taskId}`, data));
}

export function publishTask(taskId: string) {
  return unwrap<LearningTask>(client.post(`/admin/learning/tasks/${taskId}/publish`));
}

export function archiveTask(taskId: string) {
  return unwrap<LearningTask>(client.post(`/admin/learning/tasks/${taskId}/archive`));
}

export function deleteTask(taskId: string) {
  return unwrap<{ task_id: string; deleted: boolean }>(client.delete(`/admin/learning/tasks/${taskId}`));
}

// ── Admin: Task Items ──

export function addTaskItem(taskId: string, data: {
  item_type: string;
  title: string;
  resource_id?: string;
  knowledge_point_id?: string;
  config?: Record<string, unknown>;
  sort_order?: number;
}) {
  return unwrap<TaskItem>(client.post(`/admin/learning/tasks/${taskId}/items`, data));
}

export function removeTaskItem(taskId: string, itemId: string) {
  return unwrap<{ item_id: string; deleted: boolean }>(
    client.delete(`/admin/learning/tasks/${taskId}/items/${itemId}`),
  );
}
