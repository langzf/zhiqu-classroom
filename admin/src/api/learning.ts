import api from './client'
import type { ApiResponse, PaginatedData, LearningTask, TaskItem } from '@zhiqu/shared'

/* ── Tasks ────────────────────────────────────────── */

export interface TaskListParams {
  page?: number
  page_size?: number
  status?: string
  task_type?: string
}

export const listTasks = (params?: TaskListParams) =>
  api.get<ApiResponse<PaginatedData<LearningTask>>>('/admin/learning/tasks', { params })

export const getTask = (taskId: string) =>
  api.get<ApiResponse<LearningTask>>(`/admin/learning/tasks/${taskId}`)

export const createTask = (data: Partial<LearningTask>) =>
  api.post<ApiResponse<LearningTask>>('/admin/learning/tasks', data)

export const updateTask = (taskId: string, data: Partial<LearningTask>) =>
  api.patch<ApiResponse<LearningTask>>(`/admin/learning/tasks/${taskId}`, data)

export const deleteTask = (taskId: string) =>
  api.delete<ApiResponse<null>>(`/admin/learning/tasks/${taskId}`)

export const publishTask = (taskId: string) =>
  api.post<ApiResponse<LearningTask>>(`/admin/learning/tasks/${taskId}/publish`)

/* ── Task Items ───────────────────────────────────── */

export const listTaskItems = (taskId: string) =>
  api.get<ApiResponse<TaskItem[]>>(`/admin/learning/tasks/${taskId}/items`)

export const addTaskItem = (taskId: string, data: Partial<TaskItem>) =>
  api.post<ApiResponse<TaskItem>>(`/admin/learning/tasks/${taskId}/items`, data)

export const updateTaskItem = (taskId: string, itemId: string, data: Partial<TaskItem>) =>
  api.patch<ApiResponse<TaskItem>>(`/admin/learning/tasks/${taskId}/items/${itemId}`, data)

export const deleteTaskItem = (taskId: string, itemId: string) =>
  api.delete<ApiResponse<null>>(`/admin/learning/tasks/${taskId}/items/${itemId}`)

/* ── Progress ─────────────────────────────────────── */

export const getTaskProgress = (taskId: string) =>
  api.get<ApiResponse<any>>(`/admin/learning/tasks/${taskId}/progress`)
