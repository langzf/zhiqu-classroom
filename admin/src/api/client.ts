import axios from 'axios';
import type { ApiResponse } from '@zhiqu/shared';
import { useAuthStore } from '@/stores/authStore';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: inject JWT ──
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: unwrap & error handling ──
client.interceptors.response.use(
  (res) => res,
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
    return Promise.reject(error);
  },
);

export default client;

/** Helper: extract ApiResponse.data from response */
export async function unwrap<T>(promise: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  const res = await promise;
  if (res.data.code !== 200 && res.data.code !== 0) {
    throw new Error(res.data.message || 'Unknown error');
  }
  return res.data.data;
}
