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

/** 发送消息（同步） */
export function sendMessage(convId: string, content: string) {
  return client.post<ApiResponse<SendMessageResponse>>(`/app/tutor/conversations/${convId}/messages`, { content }).then(unwrap);
}

/** 发送消息（流式） */
export function sendMessageStream(convId: string, content: string) {
  return client.post(`/app/tutor/conversations/${convId}/messages/stream`, { content }, { responseType: 'stream' });
}

/** 获取对话消息列表 */
export function listMessages(convId: string, params?: { page?: number; page_size?: number }) {
  return client.get<ApiResponse<PaginatedData<Message>>>(`/app/tutor/conversations/${convId}/messages`, { params }).then(unwrapPaged);
}

/** 提交消息反馈 */
export function submitFeedback(messageId: string, data: FeedbackRequest) {
  return client.post(`/app/tutor/messages/${messageId}/feedback`, data);
}
