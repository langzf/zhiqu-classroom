import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import axios from 'axios';

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60_000,
});

// 请求拦截器：注入 Authorization header
client.interceptors.request.use((config) => {
  // 从 localStorage 读取持久化的 auth state（zustand persist 格式）
  try {
    const raw = localStorage.getItem('zhiqu-app-auth');
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: { token?: string } };
      const token = parsed?.state?.token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  } catch {
    // ignore parse errors
  }
  return config;
});

// 响应拦截器：处理 401 跳转登录
client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      // 清除 auth state
      localStorage.removeItem('zhiqu-app-auth');
      // 跳转登录页
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

/** 解包 ok 包装 */
export function unwrap<T>(resp: { data: ApiResponse<T> }): T {
  const body = resp.data;
  if (body.code !== 0) throw new Error(body.message ?? 'request failed');
  return body.data as T;
}

/** 解包分页 ok 包装 */
export function unwrapPaged<T>(resp: { data: ApiResponse<PaginatedData<T>> }): PaginatedData<T> {
  const body = resp.data;
  if (body.code !== 0) throw new Error(body.message ?? 'request failed');
  return body.data as PaginatedData<T>;
}

/** 解包 ok 包装里的数组 (非分页) */
export function unwrapList<T>(resp: { data: ApiResponse<T[]> }): T[] {
  const body = resp.data;
  if (body.code !== 0) throw new Error(body.message ?? 'request failed');
  return body.data as T[];
}
