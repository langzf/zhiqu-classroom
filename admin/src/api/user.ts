import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import type { User, UserInfo } from '@zhiqu/shared';
import { client, unwrap, unwrapPaged } from './client';

/** ── 认证 ── */
export async function loginByPhone(phone: string, code?: string) {
  const tokens = await unwrap(client.post<ApiResponse<{ access_token: string; refresh_token?: string; token_type: string; expires_in: number }>>('/auth/login/admin', { phone, code }));
  // 登录后用新 token 拉取用户信息
  const user = await unwrap(client.get<ApiResponse<UserInfo>>('/app/user/me', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  }));
  return { ...tokens, user };
}

/** 发送验证码（MVP 阶段暂为空实现） */
export async function sendCode(phone: string) {
  // MVP: 后端暂未实现短信发送，直接 resolve
  return Promise.resolve();
}

/** ── 当前用户 ── */
export function getMe() {
  return client.get<ApiResponse<UserInfo>>('/app/user/me').then(unwrap);
}

/** ── 管理：用户列表 ── */
export function listUsers(params: { role?: string; keyword?: string; page?: number; page_size?: number } = {}) {
  return client.get<ApiResponse<PaginatedData<User>>>('/admin/users', { params }).then(unwrapPaged);
}

/** ── 管理：用户详情 ── */
export function getUser(userId: string) {
  return client.get<ApiResponse<User>>(`/admin/users/${userId}`).then(unwrap);
}

/** ── 管理：更新用户（含 role, is_active 等） ── */
export function updateUser(userId: string, data: Partial<{ nickname: string; role: string; is_active: boolean }>) {
  return client.patch<ApiResponse<User>>(`/admin/users/${userId}`, data).then(unwrap);
}
