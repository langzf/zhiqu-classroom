import { client as api, unwrap } from './client'
import type {
  ApiResponse,
  TokenOut,
  UserInfo,
  RegisterRequest,
} from '@zhiqu/shared'

/* ── Auth（/auth 前缀，不在 /app 下）───────────────── */

export const login = (data: { phone: string; code: string }) =>
  api.post<ApiResponse<TokenOut>>('/auth/login', data)

export const register = (data: RegisterRequest) =>
  api.post<ApiResponse<TokenOut>>('/auth/register', data)

/** LoginPage 使用：接收 (phone, code) 两个参数，返回解包后的 TokenOut */
export const loginByPhone = async (phone: string, code: string): Promise<TokenOut> =>
  unwrap(await api.post<ApiResponse<TokenOut>>('/auth/login', { phone, code }))

// TODO: 后端暂未实现 /auth/send-code（MVP 跳过验证码）
export const sendCode = (_phone: string) =>
  Promise.resolve({ data: { code: 0, data: null, message: 'ok' } } as any)

export const refreshToken = (refreshToken: string) =>
  api.post<ApiResponse<TokenOut>>('/auth/refresh', { refresh_token: refreshToken })

/* ── User profile（/app/user 前缀）─────────────────── */

export const getProfile = () =>
  api.get<ApiResponse<UserInfo>>('/app/user/me')

export const updateProfile = (data: Partial<UserInfo>) =>
  api.patch<ApiResponse<UserInfo>>('/app/user/me', data)

/* ── Guardian / Children ──────────────────────────── */

export const bindGuardian = (data: { guardian_phone: string }) =>
  api.post<ApiResponse<null>>('/app/user/guardian-bindings', data)

export const getChildren = () =>
  api.get<ApiResponse<UserInfo[]>>('/app/user/children')
