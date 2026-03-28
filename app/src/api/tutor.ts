import type { Conversation, Message, SendMessageResponse, FeedbackRequest } from '@zhiqu/shared';
import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged, unwrapList } from './client';

/** 获取对话列表 */
export function listConversations(params: { scene?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<Conversation>>>('/tutor/conversations', { params }).then(unwrapPaged);
}

/** 创建对话 */
export function createConversation(data: { title?: string; scene?: string }) {
  return client.post<ApiResponse<Conversation>>('/tutor/conversations', data).then(unwrap);
}

/** 获取单个对话 */
export function getConversation(id: string) {
  return client.get<ApiResponse<Conversation>>(`/tutor/conversations/${id}`).then(unwrap);
}

/** 删除对话 */
export function deleteConversation(id: string) {
  return client.delete(`/tutor/conversations/${id}`);
}

/** 发送消息（同步返回用户消息+AI回复） */
export function sendMessage(convId: string, content: string) {
  return client.post<ApiResponse<SendMessageResponse>>(`/tutor/conversations/${convId}/messages`, { content }).then(unwrap);
}

/** 获取对话消息列表 */
export function listMessages(convId: string, params?: { limit?: number; before?: string }) {
  return client.get<ApiResponse<Message[]>>(`/tutor/conversations/${convId}/messages`, { params }).then(unwrapList);
}

/** 提交反馈 */
export function submitFeedback(convId: string, data: FeedbackRequest) {
  return client.post(`/tutor/conversations/${convId}/feedback`, data);
}
