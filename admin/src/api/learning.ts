import client from './client';
import type { LearningTask, LearningRecord } from '@zhiqu/shared';

/* ---------- tasks ---------- */

export async function createTask(data: {
  title: string;
  task_type: string;
  knowledge_point_id?: string;
  resource_id?: string;
  due_date?: string;
}) {
  const res = await client.post<LearningTask>('/learning/tasks', data);
  return res.data;
}

export async function listTasks(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const res = await client.get<LearningTask[]>('/learning/tasks', { params });
  return res.data;
}

export async function getTask(id: string) {
  const res = await client.get<LearningTask>(`/learning/tasks/${id}`);
  return res.data;
}

export async function updateTaskStatus(id: string, status: string) {
  const res = await client.patch(`/learning/tasks/${id}`, { status });
  return res.data;
}

/* ---------- records ---------- */

export async function submitRecord(taskId: string, data: {
  score?: number;
  answer_json?: Record<string, unknown>;
  duration_seconds?: number;
}) {
  const res = await client.post<LearningRecord>(
    `/learning/tasks/${taskId}/records`,
    data,
  );
  return res.data;
}

export async function listRecords(taskId: string) {
  const res = await client.get<LearningRecord[]>(`/learning/tasks/${taskId}/records`);
  return res.data;
}
