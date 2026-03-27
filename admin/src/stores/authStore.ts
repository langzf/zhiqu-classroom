import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserInfo } from '@zhiqu/shared';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: UserInfo | null;

  setAuth: (token: string, refreshToken: string, user: UserInfo) => void;
  setToken: (token: string) => void;
  setUser: (user: UserInfo) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,

      setAuth: (token, refreshToken, user) =>
        set({ token, refreshToken, user }),

      setToken: (token) => set({ token }),

      setUser: (user) => set({ user }),

      logout: () =>
        set({ token: null, refreshToken: null, user: null }),
    }),
    { name: 'zhiqu-admin-auth' },
  ),
);
