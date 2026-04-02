import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import type { Textbook, Chapter, KnowledgePoint, GeneratedResource } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged, unwrapList } from './client';

// ── 教材 ──

export function createTextbook(data: { title: string; subject: string; grade: string; press?: string; cover_url?: string }) {
  return client.post<ApiResponse<Textbook>>('/admin/content/textbooks', data).then(unwrap);
}

export function listTextbooks(params: { page?: number; page_size?: number; subject?: string; grade?: string } = {}) {
  return client.get<ApiResponse<PaginatedData<Textbook>>>('/admin/content/textbooks', { params }).then(unwrapPaged);
}

export function updateTextbook(id: string, data: Partial<{ title: string; subject: string; grade: string; press: string; cover_url: string }>) {
  return client.patch<ApiResponse<Textbook>>(`/admin/content/textbooks/${id}`, data).then(unwrap);
}

export function deleteTextbook(id: string) {
  return client.delete(`/admin/content/textbooks/${id}`);
}

// ── 章节 ──

export function createChapter(textbookId: string, data: { title: string; parent_id?: string; sort_order?: number }) {
  return client.post<ApiResponse<Chapter>>(`/admin/content/textbooks/${textbookId}/chapters`, data).then(unwrap);
}

export function listChapters(textbookId: string) {
  return client.get<ApiResponse<Chapter[]>>(`/admin/content/textbooks/${textbookId}/chapters`).then(unwrapList);
}

// ── 知识点 ──

export function createKnowledgePoint(chapterId: string, data: { name: string; description?: string; difficulty?: number }) {
  return client.post<ApiResponse<KnowledgePoint>>(`/admin/content/chapters/${chapterId}/knowledge-points`, data).then(unwrap);
}

export function listKnowledgePoints(chapterId: string) {
  return client.get<ApiResponse<KnowledgePoint[]>>(`/admin/content/chapters/${chapterId}/knowledge-points`).then(unwrapList);
}

export function updateKnowledgePoint(kpId: string, data: Partial<{ name: string; description: string; difficulty: number }>) {
  return client.patch<ApiResponse<KnowledgePoint>>(`/admin/content/knowledge-points/${kpId}`, data).then(unwrap);
}

export function deleteKnowledgePoint(kpId: string) {
  return client.delete(`/admin/content/knowledge-points/${kpId}`);
}

// ── 资源生成 ──

export function generateResource(kpId: string, data: { resource_type?: string; template_id?: string }) {
  return client.post<ApiResponse<GeneratedResource>>(`/admin/content/knowledge-points/${kpId}/generate-resource`, data).then(unwrap);
}

export function listResources(kpId: string) {
  return client.get<ApiResponse<GeneratedResource[]>>(`/admin/content/knowledge-points/${kpId}/resources`).then(unwrapList);
}

// ── 习题 ──

export function generateExercises(data: { knowledge_point_id: string; count?: number; exercise_type?: string }) {
  return client.post<ApiResponse<unknown>>('/admin/content/exercises/generate', data).then(unwrap);
}

export function createExercise(data: { knowledge_point_id: string; question: string; exercise_type: string; options?: unknown; answer: string; explanation?: string }) {
  return client.post<ApiResponse<unknown>>('/admin/content/exercises', data).then(unwrap);
}

export function listExercises(params: { knowledge_point_id?: string; exercise_type?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<unknown>>>('/admin/content/exercises', { params }).then(unwrapPaged);
}

// ── 提示词模板 ──

export function createPromptTemplate(data: { name: string; template: string; scene?: string }) {
  return client.post<ApiResponse<unknown>>('/admin/content/prompt-templates', data).then(unwrap);
}

export function listPromptTemplates(params: { scene?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<unknown>>>('/admin/content/prompt-templates', { params }).then(unwrapPaged);
}

export function getPromptTemplate(id: string) {
  return client.get<ApiResponse<unknown>>(`/admin/content/prompt-templates/${id}`).then(unwrap);
}

export function updatePromptTemplate(id: string, data: Partial<{ name: string; template: string; scene: string }>) {
  return client.patch<ApiResponse<unknown>>(`/admin/content/prompt-templates/${id}`, data).then(unwrap);
}

export function deletePromptTemplate(id: string) {
  return client.delete(`/admin/content/prompt-templates/${id}`);
}
