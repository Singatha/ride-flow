import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiRequest } from './client'

describe('apiRequest', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('sends cookies and bearer credentials without persisting tokens', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 'user-id' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/users/me', { accessToken: 'access-token' })

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/users/me',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({ Authorization: 'Bearer access-token' }),
      }),
    )
  })

  it('turns the standard backend error envelope into an ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ error: { code: 'INVALID_TOKEN', message: 'Token expired' } }),
    }))

    const request = apiRequest('/users/me')

    await expect(request).rejects.toEqual(new ApiError(401, 'INVALID_TOKEN', 'Token expired'))
  })
})
