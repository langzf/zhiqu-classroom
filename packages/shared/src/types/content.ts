import type { ParseStatus, Subject } from '../constants/enums';

/** 教材 */
export interface Textbook {
  id: string;
  title: string;
  subject: Subject;
  grade_range: string | null;
  source_file_url: string | null;
  cover_url: string | null;
  parse_status: ParseStatus;
  metadata_: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

/** 章节 */
export interface Chapter {
  id: string;
  textbook_id: string;
  parent_id: string | null;
  title: string;
  sort_order: number;
  level: number;
  children?: Chapter[];
}

/** 知识点 */
export interface KnowledgePoint {
  id: string;
  chapter_id: string;
  title: string;
  description: string | null;
  difficulty: number;
  importance: number;
  sort_order: number;
  tags: string[];
}

/** 生成资源（练习题等） */
export interface GeneratedResource {
  id: string;
  knowledge_point_id: string;
  resource_type: string;
  title: string;
  content_json: Record<string, unknown>;
  llm_model: string | null;
  quality_score: number | null;
  prompt_template_id: string | null;
  created_at: string;
}
