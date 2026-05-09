import type { Conversation, Message, SendMessageResponse, FeedbackRequest } from '@zhiqu/shared';
import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged, unwrapList } from './client';

/** 获取对话列表 */
export function listConversations(params: { scene?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<Conversation>>>('/app/tutor/conversations', { params }).then(unwrapPaged);
}

/** 创建对话 */
export function createConversation(data: { title?: string; scene?: string }) {
  return client.post<ApiResponse<Conversation>>('/app/tutor/conversations', data).then(unwrap);
}

/** 获取单个对话 */
export function getConversation(id: string) {
  return client.get<ApiResponse<Conversation>>(`/app/tutor/conversations/${id}`).then(unwrap);
}

/** 更新对话 */
export function updateConversation(id: string, data: { title?: string }) {
  return client.patch<ApiResponse<Conversation>>(`/app/tutor/conversations/${id}`, data).then(unwrap);
}

/** 删除对话 */
export function deleteConversation(id: string) {
  return client.delete(`/app/tutor/conversations/${id}`);
}

/** 发送消息（流式 SSE） */
export async function sendMessageStream(
  convId: string,
  content: string,
  onChunk: (text: string) => void,
  onDone?: (fullText: string) => void,
  onError?: (err: Error) => void,
): Promise<void> {
  const baseURL = client.defaults.baseURL || '/api/v1';

  // 从 localStorage 读取 token（与 client 拦截器逻辑一致）
  let token: string | undefined;
  try {
    const raw = localStorage.getItem('zhiqu-app-auth');
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: { token?: string } };
      token = parsed?.state?.token;
    }
  } catch { /* ignore */ }

  try {
    const response = await fetch(`${baseURL}/app/tutor/conversations/${convId}/messages`, {
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

    if (contentType.includes('text/event-stream') && response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
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
              fullText += data;
              onChunk(data);
            }
          }
        }
      }
      onDone?.(fullText);
    } else {
      // fallback: JSON 非流式
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

/** 发送消息（非流式，已弃用，保留兼容） */
export function sendMessage(convId: string, content: string) {
  return client.post<ApiResponse<SendMessageResponse>>(`/app/tutor/conversations/${convId}/messages`, { content }).then(unwrap);
}

/** 获取对话消息列表 */
export function listMessages(convId: string, params?: { page?: number; page_size?: number }) {
  return client.get<ApiResponse<PaginatedData<Message>>>(`/app/tutor/conversations/${convId}/messages`, { params }).then(unwrapPaged);
}

/** 提交消息反馈 */
export function submitFeedback(messageId: string, data: FeedbackRequest) {
  return client.post(`/app/tutor/messages/${messageId}/feedback`, data);
}
