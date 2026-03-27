/** 对话 */
export interface Conversation {
  id: string;
  user_id: string;
  knowledge_point_id: string | null;
  title: string;
  status: string;
  model_name: string | null;
  system_prompt: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

/** 消息 */
export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  token_count: number | null;
  metadata_: Record<string, unknown> | null;
  created_at: string;
}
