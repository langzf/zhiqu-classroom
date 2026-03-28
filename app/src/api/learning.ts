import type { LearningTask, TaskItem, SubmitProgressRequest } from '@zhiqu/shared';
import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged, unwrapList } from './client';

/** 获取学习任务列表 */
export function listTasks(params?: { status?: string; page?: number; page_size?: number }) {
  return client.get<ApiResponse<PaginatedData<LearningTask>>>('/learning/tasks', { params }).then(unwrapPaged);
}

/** 创建学习任务 */
export function createTask(data: { title: string; task_type: string; config_json?: Record<string, unknown> }) {
  return client.post<ApiResponse<LearningTask>>('/learning/tasks', data).then(unwrap);
}

/** 获取单个任务详情 */
export function getTask(taskId: string) {
  return client.get<ApiResponse<LearningTask>>(`/learning/tasks/${taskId}`).then(unwrap);
}

/** 获取任务项列表 */
export function listTaskItems(taskId: string) {
  return client.get<ApiResponse<TaskItem[]>>(`/learning/tasks/${taskId}/items`).then(unwrapList);
}

/** 提交任务项进度 */
export function submitProgress(taskId: string, itemId: string, data: SubmitProgressRequest) {
  return client.post<ApiResponse<TaskItem>>(`/learning/tasks/${taskId}/items/${itemId}/progress`, data).then(unwrap);
}
