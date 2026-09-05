import { apiRequest } from './client'
import type { DriverLocation, DriverProfile, Vehicle, VehicleCategory } from './types'

export type CreateDriverProfileInput = {
  license_number: string
  license_expiry: string
}

export type CreateVehicleInput = {
  make: string
  model: string
  year: number
  color: string
  license_plate: string
  category: VehicleCategory
  is_active?: boolean
}

export type UpdateDriverLocationInput = {
  latitude: number
  longitude: number
  heading?: number | null
  speed_kph?: number | null
  accuracy_m?: number | null
  recorded_at?: string
}

export function getDriverProfile(accessToken: string) {
  return apiRequest<DriverProfile>('/drivers/me', { accessToken })
}

export function createDriverProfile(accessToken: string, input: CreateDriverProfileInput) {
  return apiRequest<DriverProfile>('/drivers/profile', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(input),
  })
}

export function setDriverAvailability(accessToken: string, online: boolean) {
  return apiRequest<DriverProfile>(`/drivers/status/${online ? 'online' : 'offline'}`, {
    method: 'PUT',
    accessToken,
  })
}

export function updateDriverLocation(accessToken: string, input: UpdateDriverLocationInput) {
  return apiRequest<DriverLocation>('/drivers/location', {
    method: 'PUT',
    accessToken,
    body: JSON.stringify(input),
  })
}

export function listVehicles(accessToken: string) {
  return apiRequest<Vehicle[]>('/vehicles/me', { accessToken })
}

export function createVehicle(accessToken: string, input: CreateVehicleInput) {
  return apiRequest<Vehicle>('/vehicles', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(input),
  })
}

export function activateVehicle(accessToken: string, vehicleId: string) {
  return apiRequest<Vehicle>(`/vehicles/${vehicleId}`, {
    method: 'PATCH',
    accessToken,
    body: JSON.stringify({ is_active: true }),
  })
}
