import { beforeEach, describe, expect, it } from 'vitest'

import type { AuthSession } from '../api/types'
import { useAuthStore } from './authStore'

const session: AuthSession = {
  access_token: 'access-token',
  refresh_token: 'not-stored',
  token_type: 'bearer',
  expires_in: 900,
  user: {
    id: 'user-id',
    email: 'rider@example.com',
    role: 'RIDER',
    first_name: 'Amina',
    last_name: 'Dlamini',
    phone_number: null,
    is_active: true,
    created_at: '2026-09-06T00:00:00Z',
    updated_at: '2026-09-06T00:00:00Z',
  },
}

describe('authStore', () => {
  beforeEach(() => useAuthStore.setState({
    accessToken: null,
    accessTokenExpiresAt: null,
    user: null,
    status: 'checking',
  }))

  it('retains only the access token and user from a session', () => {
    useAuthStore.getState().setSession(session)

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-token')
    expect(state.accessTokenExpiresAt).toBeGreaterThan(Date.now())
    expect(state.user?.email).toBe('rider@example.com')
    expect(state).not.toHaveProperty('refreshToken')
  })

  it('clears authentication state on logout', () => {
    useAuthStore.getState().setSession(session)
    useAuthStore.getState().clearSession()

    expect(useAuthStore.getState()).toMatchObject({
      accessToken: null,
      accessTokenExpiresAt: null,
      user: null,
      status: 'anonymous',
    })
  })
})
