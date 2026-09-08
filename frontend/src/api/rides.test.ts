import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  cancelRide,
  estimateRide,
  getCurrentRideOffer,
  performDriverRideAction,
  rejectRideOffer,
  requestRide,
} from './rides'

const rideInput = {
  pickup: { latitude: -26.2041, longitude: 28.0473 },
  destination: { latitude: -26.1076, longitude: 28.0567 },
  ride_type: 'STANDARD' as const,
}

describe('ride API', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uses the same coordinates for estimates and requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await estimateRide('token', rideInput)
    await requestRide('token', rideInput)

    expect(fetchMock.mock.calls[0][0]).toContain('/rides/estimate')
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/rides$/)
    expect(fetchMock.mock.calls[0][1].body).toBe(JSON.stringify(rideInput))
    expect(fetchMock.mock.calls[1][1].body).toBe(JSON.stringify(rideInput))
  })

  it('maps driver lifecycle commands to explicit operation endpoints', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await performDriverRideAction('token', 'ride-id', 'arriving')
    await performDriverRideAction('token', 'ride-id', 'complete')

    expect(fetchMock.mock.calls[0][0]).toContain('/rides/ride-id/arriving')
    expect(fetchMock.mock.calls[1][0]).toContain('/rides/ride-id/complete')
  })

  it('loads and rejects only the targeted driver offer', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await getCurrentRideOffer('token')
    await rejectRideOffer('token', 'ride-id')

    expect(fetchMock.mock.calls[0][0]).toContain('/rides/offers/current')
    expect(fetchMock.mock.calls[1][0]).toContain('/rides/ride-id/reject')
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: 'POST' }))
  })

  it('cancels through the rider operation rather than a status patch', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await cancelRide('token', 'ride-id')

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/rides/ride-id/cancel'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
