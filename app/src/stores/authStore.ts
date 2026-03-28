import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserInfo, TokenOut } from '@zhiqu/shared';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: UserInfo | null;
  setAuth: (data: TokenOut) => void;
  setUser: (user: UserInfo) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      setAuth: (data) =>
        set({
          token: data.access_token,
          refreshToken: data.refresh_token,
          user: data.user,
        }),
      setUser: (user) => set({ user }),
      logout: () =>
        set({
          token: null,
          refreshToken: null,
          user: null,
        }),
    }),
    { name: 'zhiqu-app-auth' },
  ),
);
