import { afterEach, describe, expect, it, vi } from 'vitest'

import { getHealth } from './health'

describe('getHealth', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('returns the typed API health response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'ok' }),
      }),
    )

    await expect(getHealth()).resolves.toEqual({ status: 'ok' })
  })

  it('rejects an unhealthy response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))

    await expect(getHealth()).rejects.toThrow('Health check failed with status 503')
  })
})

