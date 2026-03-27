import client, { unwrap } from './client';
import type { Textbook, Chapter, KnowledgePoint, GeneratedResource, PaginatedData } from '@zhiqu/shared';

// ── Textbooks ──
export function listTextbooks(params?: { page?: number; page_size?: number; subject?: string }) {
  return unwrap<PaginatedData<Textbook>>(client.get('/content/textbooks', { params }));
}

export function getTextbook(id: string) {
  return unwrap<Textbook>(client.get(`/content/textbooks/${id}`));
}

export function createTextbook(data: { title: string; subject: string; grade_range?: string }) {
  return unwrap<Textbook>(client.post('/content/textbooks', data));
}

export function updateTextbook(id: string, data: { title?: string; subject?: string }) {
  return unwrap<Textbook>(client.patch(`/content/textbooks/${id}`, data));
}

export function uploadTextbook(file: File, title: string, subject: string) {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  form.append('subject', subject);
  return unwrap<Textbook>(
    client.post('/content/textbooks/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    }),
  );
}

export function triggerParse(textbookId: string) {
  return unwrap<{ task_id: string }>(client.post(`/content/textbooks/${textbookId}/parse`));
}

// ── Chapters ──
export function getChapterTree(textbookId: string) {
  return unwrap<Chapter[]>(client.get(`/content/textbooks/${textbookId}/chapters`));
}

// ── Knowledge Points ──
export function getKnowledgePoints(chapterId: string) {
  return unwrap<KnowledgePoint[]>(client.get(`/content/chapters/${chapterId}/knowledge-points`));
}

export function searchKnowledgePoints(data: { query: string; limit?: number }) {
  return unwrap<KnowledgePoint[]>(client.post('/content/knowledge-points/search', data));
}

// ── Generated Resources (Exercises) ──
export function generateExercises(data: {
  knowledge_point_id: string;
  exercise_type?: string;
  count?: number;
  difficulty?: number;
}) {
  return unwrap<GeneratedResource>(client.post('/content/exercises/generate', data));
}

export function getExercise(resourceId: string) {
  return unwrap<GeneratedResource>(client.get(`/content/exercises/${resourceId}`));
}

export function listExercises(params?: {
  exercise_type?: string;
  limit?: number;
  offset?: number;
}) {
  return unwrap<GeneratedResource[]>(client.get('/content/exercises', { params }));
}
