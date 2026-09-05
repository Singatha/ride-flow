import { afterEach, describe, expect, it, vi } from 'vitest'

import { activateVehicle, setDriverAvailability, updateDriverLocation } from './drivers'

describe('driver API', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uses explicit availability operations', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await setDriverAvailability('token', true)
    await setDriverAvailability('token', false)

    expect(fetchMock.mock.calls[0][0]).toContain('/drivers/status/online')
    expect(fetchMock.mock.calls[1][0]).toContain('/drivers/status/offline')
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: 'PUT' }))
  })

  it('publishes latitude before longitude without client-side coordinate swapping', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await updateDriverLocation('token', { latitude: -26.2041, longitude: 28.0473 })

    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string) as Record<string, number>
    expect(body).toEqual({ latitude: -26.2041, longitude: 28.0473 })
  })

  it('activates one owned vehicle through the patch endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await activateVehicle('token', 'vehicle-id')

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/vehicles/vehicle-id'),
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ is_active: true }) }),
    )
  })
})
