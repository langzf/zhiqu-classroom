import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import type { Textbook, Chapter, KnowledgePoint, GeneratedResource } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged, unwrapList } from './client';

/** ── 教材 ── */
export function listTextbooks(params: { page?: number; page_size?: number; subject?: string; grade?: string } = {}) {
  return client.get<ApiResponse<PaginatedData<Textbook>>>('/content/textbooks', { params }).then(unwrapPaged);
}

export function getTextbook(id: string) {
  return client.get<ApiResponse<Textbook>>(`/content/textbooks/${id}`).then(unwrap);
}

/** ── 章节 ── */
export function listChapters(textbookId: string) {
  return client.get<ApiResponse<Chapter[]>>(`/content/textbooks/${textbookId}/chapters`).then(unwrapList);
}

/** ── 知识点 ── */
export function listKnowledgePoints(params: { chapter_id?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<KnowledgePoint>>>('/content/knowledge-points', { params }).then(unwrapPaged);
}

export function getKnowledgePoint(id: string) {
  return client.get<ApiResponse<KnowledgePoint>>(`/content/knowledge-points/${id}`).then(unwrap);
}

/** ── 练习题 ── */
export function listExercises(params: { exercise_type?: string; limit?: number; offset?: number } = {}) {
  return client.get<ApiResponse<GeneratedResource[]>>('/content/exercises', { params }).then(unwrapList);
}

/** ── 知识点的资源（练习题等）── */
export function listKpResources(kpId: string) {
  return client.get<ApiResponse<GeneratedResource[]>>(`/content/knowledge-points/${kpId}/resources`).then(unwrapList);
}

/** ── 搜索知识点 ── */
export function searchKnowledgePoints(query: string, topK?: number) {
  return client.post<ApiResponse<KnowledgePoint[]>>('/content/knowledge-points/search', { query, top_k: topK ?? 5 }).then(unwrapList);
}
