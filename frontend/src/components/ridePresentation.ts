import type { Ride } from '../api/types'

const terminalStatuses = new Set<Ride['status']>(['COMPLETED', 'CANCELLED'])

export function rideStatusColour(status: Ride['status']) {
  if (status === 'COMPLETED') return 'green'
  if (status === 'CANCELLED') return 'red'
  if (status === 'IN_PROGRESS') return 'blue'
  if (status === 'SEARCHING') return 'gold'
  return 'cyan'
}

export function isActiveRide(ride: Ride) {
  return !terminalStatuses.has(ride.status)
}
