import client, { unwrap } from './client';
import type { TokenOut, UserInfo, LoginRequest, RegisterRequest } from '@zhiqu/shared';

/** 登录 */
export function login(data: LoginRequest) {
  return unwrap<TokenOut>(client.post('/user/login', data));
}

/** 注册 */
export function register(data: RegisterRequest) {
  return unwrap<TokenOut>(client.post('/user/register', data));
}

/** 获取当前用户信息 */
export function getMe() {
  return unwrap<UserInfo>(client.get('/user/me'));
}

/** 更新当前用户信息 */
export function updateMe(data: Partial<Pick<UserInfo, 'nickname' | 'avatar_url'>>) {
  return unwrap<UserInfo>(client.patch('/user/me', data));
}

/** 刷新 token */
export function refreshToken(refresh_token: string) {
  return unwrap<{ access_token: string; token_type: string }>(
    client.post('/user/refresh', { refresh_token }),
  );
}

/** 获取用户列表（管理员） */
export async function listUsers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
}) {
  const res = await client.get('/user/users', { params });
  return res.data?.data ?? res.data;
}
