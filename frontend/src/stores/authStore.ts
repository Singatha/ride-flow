import { create } from 'zustand'

import type { AuthSession, User } from '../api/types'

type AuthStatus = 'checking' | 'authenticated' | 'anonymous'

type AuthState = {
  accessToken: string | null
  accessTokenExpiresAt: number | null
  user: User | null
  status: AuthStatus
  setSession: (session: AuthSession) => void
  setUser: (user: User) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  accessTokenExpiresAt: null,
  user: null,
  status: 'checking',
  setSession: (session) => set({
    accessToken: session.access_token,
    accessTokenExpiresAt: Date.now() + session.expires_in * 1000,
    user: session.user,
    status: 'authenticated',
  }),
  setUser: (user) => set({ user }),
  clearSession: () => set({
    accessToken: null,
    accessTokenExpiresAt: null,
    user: null,
    status: 'anonymous',
  }),
}))
