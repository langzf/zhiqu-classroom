import type { ApiResponse, TokenOut, UserInfo } from '@zhiqu/shared';
import { client, unwrap } from './client';

/** MVP: 后端跳过验证码验证，此函数仅做 UI 兼容 */
export function sendCode(_phone: string) {
  return Promise.resolve();
}

/** 手机号登录（MVP 跳过验证码） */
export function loginByPhone(phone: string, code: string) {
  return client.post<ApiResponse<TokenOut>>('/user/login', { phone, code }).then(unwrap);
}

/** 获取当前用户信息 */
export function getMe() {
  return client.get<ApiResponse<UserInfo>>('/user/me').then(unwrap);
}

/** 更新当前用户信息 */
export function updateMe(data: Partial<Pick<UserInfo, 'nickname' | 'avatar_url' | 'grade' | 'school'>>) {
  return client.patch<ApiResponse<UserInfo>>('/user/me', data).then(unwrap);
}

/** 刷新 token */
export function refreshToken(refresh_token: string) {
  return client.post<ApiResponse<{ access_token: string; token_type: string; expires_in: number }>>('/user/refresh', { refresh_token }).then(unwrap);
}
