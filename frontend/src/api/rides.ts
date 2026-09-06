import { apiRequest } from './client'
import type { Coordinates, FareEstimate, Ride, RideType } from './types'

export type RideRequestInput = {
  pickup: Coordinates
  destination: Coordinates
  ride_type: RideType
}

export type DriverRideAction = 'accept' | 'arriving' | 'arrive' | 'start' | 'complete'

export function estimateRide(accessToken: string, input: RideRequestInput) {
  return apiRequest<FareEstimate>('/rides/estimate', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(input),
  })
}

export function requestRide(accessToken: string, input: RideRequestInput) {
  return apiRequest<Ride>('/rides', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(input),
  })
}

export function listMyRides(accessToken: string) {
  return apiRequest<Ride[]>('/rides', { accessToken })
}

export function listAvailableRides(accessToken: string) {
  return apiRequest<Ride[]>('/rides/available', { accessToken })
}

export function cancelRide(accessToken: string, rideId: string) {
  return apiRequest<Ride>(`/rides/${rideId}/cancel`, {
    method: 'POST',
    accessToken,
  })
}

export function performDriverRideAction(
  accessToken: string,
  rideId: string,
  action: DriverRideAction,
) {
  return apiRequest<Ride>(`/rides/${rideId}/${action}`, {
    method: 'POST',
    accessToken,
  })
}
