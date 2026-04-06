import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import type { LearningTask, TaskProgress, SubmitProgressRequest } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged } from './client';

// ── Backend schemas (local mirrors) ──
export interface TaskOut {
  id: string;
  title: string;
  task_type: string;
  status: string;
  created_at: string;
  due_date?: string;
}

export interface TaskDetail extends TaskOut {
  items: unknown[];
}

export interface ProgressOut {
  id: string;
  task_id: string;
  student_id: string;
  status: string;
  score?: number;
  started_at?: string;
  completed_at?: string;
}

export interface MasteryRecordOut {
  id: string;
  student_id: string;
  knowledge_point_id: string;
  mastery_level: number;
  updated_at: string;
}

export interface StudySessionOut {
  id: string;
  student_id: string;
  knowledge_point_id?: string;
  session_type: string;
  started_at: string;
  ended_at?: string;
}

// ── 任务编排（教师分配的任务，学生视角）──

export function listMyTasks(params: { status?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<TaskOut>>>('/app/learning/tasks', { params }).then(unwrapPaged);
}

export function listTasks(params: { status?: string; page?: number; page_size?: number } = {}) {
  return listMyTasks(params);
}

export function getTask(taskId: string) {
  return client.get<ApiResponse<TaskDetail>>(`/app/learning/tasks/${taskId}`).then(unwrap);
}

// TODO: 后端尚无独立的 task-items 端点；TaskDetail.items 已含子项，此处返回 task.items
export async function listTaskItems(taskId: string) {
  const task = await getTask(taskId);
  return (task as TaskDetail).items ?? [];
}

export function startTask(taskId: string) {
  return client.post<ApiResponse<ProgressOut>>(`/app/learning/tasks/${taskId}/start`).then(unwrap);
}

export function submitTask(taskId: string, data: SubmitProgressRequest) {
  return client.post<ApiResponse<ProgressOut>>(`/app/learning/tasks/${taskId}/submit`, data).then(unwrap);
}

// ── 学习任务（LearningCoreService，学生自主学习）──

export function listLearningTasks(params: { status?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<LearningTask>>>('/app/learning/learning-tasks', { params }).then(unwrapPaged);
}

export function submitLearningTask(taskId: string, data: { score?: number; answer_snapshot?: unknown }) {
  return client.post<ApiResponse<LearningTask>>(`/app/learning/learning-tasks/${taskId}/submit`, data).then(unwrap);
}

// ── 掌握度 ──

export function listMastery(params: { page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<MasteryRecordOut>>>('/app/learning/mastery', { params }).then(unwrapPaged);
}

// ── 学习会话 ──

export function createStudySession(data: { knowledge_point_id?: string; session_type?: string }) {
  return client.post<ApiResponse<StudySessionOut>>('/app/learning/study-sessions', data).then(unwrap);
}

export function listStudySessions(params: { page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<StudySessionOut>>>('/app/learning/study-sessions', { params }).then(unwrapPaged);
}

// ── 学习概览 ──

export function getMyProgress() {
  return client.get<ApiResponse<unknown>>('/app/learning/progress').then(unwrap);
}
