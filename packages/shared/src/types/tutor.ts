/** 对话场景 */
export type ConversationScene =
  | 'free_chat'
  | 'homework_help'
  | 'concept_explain'
  | 'review_guide'
  | 'error_analysis';

/** 对话场景标签 */
export const SCENE_LABELS: Record<ConversationScene, string> = {
  free_chat: '自由对话',
  homework_help: '作业辅导',
  concept_explain: '概念讲解',
  review_guide: '复习指导',
  error_analysis: '错题分析',
};

/** 对话 (后端 ConversationOut) */
export interface Conversation {
  id: string;
  student_id: string;
  title: string;
  scene: ConversationScene;
  model_config: Record<string, unknown> | null;
  summary: string | null;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

/** 消息 (后端 MessageOut) */
export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  token_count: number | null;
  created_at: string;
}

/** 发送消息响应 */
export interface SendMessageResponse {
  user_msg: Message;
  assistant_msg: Message;
}

/** 反馈请求 */
export interface FeedbackRequest {
  message_id: string;
  rating: number;
  comment?: string;
}
