import type { UserRole } from '../constants/enums';

/** 用户信息 */
export interface UserInfo {
  id: string;
  phone: string;
  role: UserRole;
  nickname: string | null;
  avatar_url: string | null;
  grade: string | null;
  school: string | null;
  created_at: string;
}

/** 学生档案 */
export interface StudentProfile {
  id: string;
  user_id: string;
  school_name: string | null;
  grade: string | null;
  learning_preference: Record<string, unknown> | null;
}

/** Token 响应 */
export interface TokenOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
}

/** 登录请求 */
export interface LoginRequest {
  phone: string;
  code?: string;
}

/** 注册请求 */
export interface RegisterRequest {
  phone: string;
  nickname: string;
  role?: string;
  code?: string;
}

/** User 别名（admin 管理场景） */
export interface User extends UserInfo {
  updated_at?: string;
}
