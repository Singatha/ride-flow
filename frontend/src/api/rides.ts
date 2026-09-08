import { apiRequest } from './client'
import type { Coordinates, FareEstimate, Ride, RideType } from './types'

export type RideRequestInput = {
  pickup: Coordinates
  destination: Coordinates
  ride_type: RideType
}

export type DriverRideAction = 'accept' | 'arriving' | 'arrive' | 'start' | 'complete'

export type RideOffer = {
  ride: Ride
  distance_m: string
  offered_at: string
  expires_at: string
}

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

export function getCurrentRideOffer(accessToken: string) {
  return apiRequest<RideOffer | null>('/rides/offers/current', { accessToken })
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

export function rejectRideOffer(accessToken: string, rideId: string) {
  return apiRequest<void>(`/rides/${rideId}/reject`, {
    method: 'POST',
    accessToken,
  })
}
