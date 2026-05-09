import type { ApiResponse, PaginatedData } from '@zhiqu/shared';
import axios, { type InternalAxiosRequestConfig } from 'axios';
import {
  applyTraceHeaders,
  childSpan,
  createTraceContext,
  installGlobalTraceHandlers,
  reportTraceLog,
  type TraceContext,
} from './trace';

interface TracedAxiosConfig extends InternalAxiosRequestConfig {
  traceContext?: TraceContext;
  traceStartedAt?: number;
}

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60_000,
});

installGlobalTraceHandlers();

// 请求拦截器：注入 Authorization header
client.interceptors.request.use((config) => {
  const tracedConfig = config as TracedAxiosConfig;
  const rootTrace = createTraceContext();
  const requestTrace = childSpan(rootTrace);
  tracedConfig.traceContext = requestTrace;
  tracedConfig.traceStartedAt = performance.now();
  config.headers = config.headers ?? {};
  applyTraceHeaders(config.headers as unknown as Record<string, unknown>, requestTrace);

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
  (response) => {
    const config = response.config as TracedAxiosConfig;
    reportTraceLog(response.status >= 400 ? 'warn' : 'info', 'frontend request finished', {
      traceContext: config.traceContext,
      path: response.config.url,
      method: response.config.method?.toUpperCase(),
      statusCode: response.status,
      durationMs: elapsedMs(config.traceStartedAt),
      meta: { app: 'student' },
    });
    return response;
  },
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      // 清除 auth state
      localStorage.removeItem('zhiqu-app-auth');
      // 跳转登录页
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    if (axios.isAxiosError(error)) {
      const config = error.config as TracedAxiosConfig | undefined;
      reportTraceLog(error.response?.status && error.response.status >= 500 ? 'error' : 'warn', 'frontend request failed', {
        traceContext: config?.traceContext,
        path: config?.url,
        method: config?.method?.toUpperCase(),
        statusCode: error.response?.status,
        durationMs: elapsedMs(config?.traceStartedAt),
        error,
        meta: { app: 'student' },
      });
    }
    return Promise.reject(error);
  },
);

function elapsedMs(startedAt: number | undefined): number | undefined {
  return typeof startedAt === 'number' ? Math.round(performance.now() - startedAt) : undefined;
}

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
