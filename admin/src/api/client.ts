import axios, { type InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@zhiqu/shared';
import { useAuthStore } from '@/stores/authStore';
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
  headers: { 'Content-Type': 'application/json' },
});

installGlobalTraceHandlers();

// ── Request interceptor: inject JWT ──
client.interceptors.request.use((config) => {
  const tracedConfig = config as TracedAxiosConfig;
  const rootTrace = createTraceContext();
  const requestTrace = childSpan(rootTrace);
  tracedConfig.traceContext = requestTrace;
  tracedConfig.traceStartedAt = performance.now();
  config.headers = config.headers ?? {};
  applyTraceHeaders(config.headers as unknown as Record<string, unknown>, requestTrace);

  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: unwrap & error handling ──
client.interceptors.response.use(
  (res) => {
    const config = res.config as TracedAxiosConfig;
    reportTraceLog(res.status >= 400 ? 'warn' : 'info', 'frontend request finished', {
      traceContext: config.traceContext,
      path: res.config.url,
      method: res.config.method?.toUpperCase(),
      statusCode: res.status,
      durationMs: elapsedMs(config.traceStartedAt),
      meta: { app: 'admin' },
    });
    return res;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      // 401 → clear auth & redirect to login
      if (status === 401 || status === 403) {
        const msg = data?.message || '';
        if (msg.includes('token') || msg.includes('expired') || status === 401) {
          useAuthStore.getState().logout();
          window.location.href = '/login';
        }
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
        meta: { app: 'admin' },
      });
    }
    return Promise.reject(error);
  },
);

function elapsedMs(startedAt: number | undefined): number | undefined {
  return typeof startedAt === 'number' ? Math.round(performance.now() - startedAt) : undefined;
}

export default client;

/** Helper: extract ApiResponse.data from response */
export async function unwrap<T>(promise: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  const res = await promise;
  if (res.data.code !== 200 && res.data.code !== 0) {
    throw new Error(res.data.message || 'Unknown error');
  }
  return res.data.data;
}

/** Helper: extract paged response { data: T[], meta } → { items, total, page, page_size } */
export interface PagedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export async function unwrapPaged<T>(
  promise: Promise<{ data: { code: number; message: string; data: { items: T[]; total: number; page: number; page_size: number; total_pages: number } } }>,
): Promise<PagedResult<T>> {
  const res = await promise;
  if (res.data.code !== 200 && res.data.code !== 0) {
    throw new Error(res.data.message || 'Unknown error');
  }
  return res.data.data as PagedResult<T>;
}

/** Helper: unwrap an array response (non-paginated) */
export async function unwrapList<T>(
  promise: Promise<{ data: { code: number; message: string; data: T[] } }>,
): Promise<T[]> {
  const res = await promise;
  if (res.data.code !== 200 && res.data.code !== 0) {
    throw new Error(res.data.message || 'Unknown error');
  }
  return res.data.data;
}
