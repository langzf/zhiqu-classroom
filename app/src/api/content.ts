import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import type { Textbook, Chapter, KnowledgePoint } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged, unwrapList } from './client';

/** ── 教材 ── */
export function listTextbooks(params: { page?: number; page_size?: number; subject?: string; grade_range?: string } = {}) {
  return client.get<ApiResponse<PaginatedData<Textbook>>>('/app/content/textbooks', { params }).then(unwrapPaged);
}

export function getTextbook(id: string) {
  return client.get<ApiResponse<Textbook>>(`/app/content/textbooks/${id}`).then(unwrap);
}

/** ── 章节 ── */
export function listChapters(textbookId: string) {
  return client.get<ApiResponse<Chapter[]>>(`/app/content/textbooks/${textbookId}/chapters`).then(unwrapList);
}

/** ── 知识点 ── */
export function listKnowledgePoints(chapterId: string) {
  return client.get<ApiResponse<KnowledgePoint[]>>(`/app/content/chapters/${chapterId}/knowledge-points`).then(unwrapList);
}

/** ── 搜索知识点 ── */
export function searchKnowledgePoints(query: string, topK?: number) {
  return client.post<ApiResponse<KnowledgePoint[]>>('/app/content/knowledge-points/search', { query, top_k: topK ?? 5 }).then(unwrapList);
}
