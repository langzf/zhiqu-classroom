import client, { unwrap, unwrapPaged, type PagedResult } from './client';
import { useAuthStore } from '@/stores/authStore';

// ── Types matching backend schemas ──

export interface Conversation {
  id: string;
  student_id: string;
  scene: string;
  title: string | null;
  knowledge_point_id: string | null;
  context_snapshot: Record<string, unknown> | null;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens_used: number | null;
  created_at: string;
}

// ── Conversations ──

export function createConversation(data: {
  scene?: string;
  title?: string;
  knowledge_point_id?: string;
  context_snapshot?: Record<string, unknown>;
}) {
  return unwrap<Conversation>(client.post('/admin/tutor/conversations', data));
}

export function listConversations(params?: {
  scene?: string;
  page?: number;
  page_size?: number;
}): Promise<PagedResult<Conversation>> {
  return unwrapPaged<Conversation>(client.get('/admin/tutor/conversations', { params }));
}

export function getConversation(convId: string) {
  return unwrap<Conversation>(client.get(`/admin/tutor/conversations/${convId}`));
}

export function updateConversation(convId: string, data: { title?: string; is_active?: boolean }) {
  return unwrap<Conversation>(client.patch(`/admin/tutor/conversations/${convId}`, data));
}

export function deleteConversation(convId: string) {
  return unwrap<{ conversation_id: string; deleted: boolean }>(
    client.delete(`/admin/tutor/conversations/${convId}`),
  );
}

// ── Messages ──

export function listMessages(convId: string, params?: { page?: number; page_size?: number }): Promise<PagedResult<Message>> {
  return unwrapPaged<Message>(
    client.get(`/admin/tutor/conversations/${convId}/messages`, { params }),
  );
}

/** Send message and receive streamed SSE response */
export async function sendMessageStream(
  convId: string,
  content: string,
  onChunk: (text: string) => void,
  onDone?: (fullText: string) => void,
  onError?: (err: Error) => void,
): Promise<void> {
  const token = useAuthStore.getState().token;
  const baseURL = client.defaults.baseURL || '/api/v1';

  try {
    const response = await fetch(`${baseURL}/tutor/conversations/${convId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get('content-type') || '';

    // If SSE streaming
    if (contentType.includes('text/event-stream') && response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        // Parse SSE lines
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              const text = parsed?.choices?.[0]?.delta?.content || parsed?.content || parsed?.text || data;
              fullText += text;
              onChunk(text);
            } catch {
              // Plain text SSE
              fullText += data;
              onChunk(data);
            }
          }
        }
      }
      onDone?.(fullText);
    } else {
      // Non-streaming JSON response
      const json = await response.json();
      const assistantMsg = json?.data?.assistant_message?.content || json?.data?.content || '';
      onChunk(assistantMsg);
      onDone?.(assistantMsg);
    }
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    onError?.(error);
  }
}

/** Send message (non-streaming, returns both user and assistant messages) */
export async function sendMessage(convId: string, content: string) {
  return unwrap<{ user_message: Message; assistant_message: Message }>(
    client.post(`/admin/tutor/conversations/${convId}/messages`, { content }),
  );
}

// ── Feedback ──

export function submitFeedback(messageId: string, data: {
  rating: number;
  comment?: string;
}) {
  return unwrap<Record<string, unknown>>(
    client.post(`/admin/tutor/messages/${messageId}/feedback`, data),
  );
}
