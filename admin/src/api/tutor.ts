import client from './client';
import type { Conversation, Message } from '@zhiqu/shared';

/* ---------- conversations ---------- */

export async function createConversation(data: {
  title?: string;
  subject?: string;
  knowledge_point_id?: string;
}) {
  const res = await client.post<Conversation>('/tutor/conversations', data);
  return res.data;
}

export async function listConversations(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const res = await client.get<Conversation[]>('/tutor/conversations', { params });
  return res.data;
}

export async function getConversation(id: string) {
  const res = await client.get<Conversation>(`/tutor/conversations/${id}`);
  return res.data;
}

export async function archiveConversation(id: string) {
  const res = await client.post(`/tutor/conversations/${id}/archive`);
  return res.data;
}

/* ---------- messages ---------- */

export async function listMessages(conversationId: string, params?: {
  limit?: number;
  offset?: number;
}) {
  const res = await client.get<Message[]>(
    `/tutor/conversations/${conversationId}/messages`,
    { params },
  );
  return res.data;
}

export async function sendMessage(conversationId: string, content: string) {
  const res = await client.post<Message>(
    `/tutor/conversations/${conversationId}/chat`,
    { content },
  );
  return res.data;
}
