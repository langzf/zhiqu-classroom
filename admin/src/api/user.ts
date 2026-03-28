import type { UserInfo, TokenOut, RegisterRequest } from '@zhiqu/shared';
import client, { unwrap, unwrapPaged, type PagedResult } from './client';

// ── Auth ────────────────────────────────────────────────

export function register(data: RegisterRequest) {
  return unwrap<TokenOut>(client.post('/user/register', data));
}

export function login(phone: string) {
  // admin 后台使用专用端点，仅允许 admin 角色登录
  return unwrap<TokenOut>(client.post('/user/login/admin', { phone }));
}

/** Alias used by LoginPage — MVP backend ignores code */
export function loginByPhone(phone: string, _code?: string) {
  return login(phone);
}

/** MVP: no-op — backend uses mock SMS provider */
export async function sendCode(_phone: string): Promise<void> {
  // no-op for MVP; backend mock always accepts any code
}

export function refreshToken() {
  return unwrap<TokenOut>(client.post('/user/refresh'));
}

// ── Profile ─────────────────────────────────────────────

export function getProfile() {
  return unwrap<UserInfo>(client.get('/user/me'));
}

export function updateProfile(data: Partial<UserInfo>) {
  return unwrap<UserInfo>(client.patch('/user/me', data));
}

// ── Admin ───────────────────────────────────────────────

export function listUsers(params?: {
  role?: string;
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<PagedResult<UserInfo>> {
  return unwrapPaged<UserInfo>(client.get('/user/users', { params }));
}

export function getUser(userId: string) {
  return unwrap<UserInfo>(client.get(`/user/users/${userId}`));
}

export function updateUser(userId: string, data: Partial<UserInfo>) {
  return unwrap<UserInfo>(client.patch(`/user/users/${userId}`, data));
}
