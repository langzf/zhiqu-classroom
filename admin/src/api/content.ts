import type { Textbook, Chapter, KnowledgePoint, GeneratedResource } from '@zhiqu/shared';
import client, { unwrap, unwrapPaged } from './client';

// ── Textbooks ──

export function createTextbook(data: { title: string; subject: string; grade: string; publisher?: string }) {
  return unwrap<Textbook>(client.post('/admin/content/textbooks', data));
}

export function uploadTextbook(form: FormData) {
  return unwrap<Textbook>(
    client.post('/admin/content/textbooks/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    }),
  );
}

export function listTextbooks(params?: { subject?: string; grade?: string; status?: string; page?: number; page_size?: number }) {
  return unwrapPaged<Textbook>(client.get('/admin/content/textbooks', { params }));
}

export function getTextbook(id: string) {
  return unwrap<Textbook>(client.get(`/admin/content/textbooks/${id}`));
}

export function updateTextbook(id: string, data: Partial<Textbook>) {
  return unwrap<Textbook>(client.patch(`/admin/content/textbooks/${id}`, data));
}

export function deleteTextbook(id: string) {
  return unwrap<void>(client.delete(`/admin/content/textbooks/${id}`));
}

export function triggerParse(textbookId: string) {
  return unwrap<Textbook>(client.post(`/admin/content/textbooks/${textbookId}/parse`));
}

// ── Chapters ──

export function getChapters(textbookId: string) {
  return unwrap<Chapter[]>(client.get(`/admin/content/textbooks/${textbookId}/chapters`));
}

// ── Knowledge Points ──

export function listKnowledgePoints(params?: { subject?: string; chapter_id?: string; page?: number; page_size?: number }) {
  return unwrapPaged<KnowledgePoint>(client.get('/admin/content/knowledge-points', { params }));
}

export function searchKnowledgePoints(data: { query: string; subject?: string; top_k?: number }) {
  return unwrap<KnowledgePoint[]>(client.post('/admin/content/knowledge-points/search', data));
}

// ── Generated Resources (Exercises) ──

export function generateExercises(data: {
  knowledge_point_id: string;
  exercise_type?: string;
  difficulty?: number;
  count?: number;
}) {
  return unwrap<GeneratedResource>(client.post('/admin/content/exercises/generate', data));
}

export function getExercise(resourceId: string) {
  return unwrap<GeneratedResource>(client.get(`/admin/content/exercises/${resourceId}`));
}

export function listExercises(params?: {
  exercise_type?: string;
  limit?: number;
  offset?: number;
}) {
  return unwrap<GeneratedResource[]>(client.get('/admin/content/exercises', { params }));
}

export function getKpResources(kpId: string) {
  return unwrap<GeneratedResource[]>(client.get(`/admin/content/knowledge-points/${kpId}/resources`));
}
