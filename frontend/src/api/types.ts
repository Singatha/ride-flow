export type UserRole = 'RIDER' | 'DRIVER' | 'ADMIN'

export type User = {
  id: string
  email: string
  role: UserRole
  first_name: string
  last_name: string
  phone_number: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type DriverVerificationStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED'
export type DriverStatus = 'OFFLINE' | 'AVAILABLE' | 'RESERVED' | 'ON_TRIP'
export type VehicleCategory = 'STANDARD' | 'PREMIUM' | 'XL'

export type DriverProfile = {
  id: string
  user_id: string
  license_number: string
  license_expiry: string
  verification_status: DriverVerificationStatus
  status: DriverStatus
  created_at: string
  updated_at: string
}

export type Vehicle = {
  id: string
  driver_id: string
  make: string
  model: string
  year: number
  color: string
  license_plate: string
  category: VehicleCategory
  is_active: boolean
  created_at: string
  updated_at: string
}

export type DriverLocation = {
  driver_id: string
  latitude: number
  longitude: number
  heading: number | null
  speed_kph: number | null
  accuracy_m: number | null
  recorded_at: string
}

export type RideType = 'STANDARD' | 'PREMIUM' | 'XL'
export type RideStatus =
  | 'REQUESTED'
  | 'SEARCHING'
  | 'DRIVER_ASSIGNED'
  | 'DRIVER_ARRIVING'
  | 'DRIVER_ARRIVED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED'

export type Coordinates = {
  latitude: number
  longitude: number
}

export type FareEstimate = {
  ride_type: RideType
  estimated_distance_km: string
  estimated_duration_minutes: string
  estimated_fare: string
  currency: string
  available_driver_count: number
}

export type AssignedDriver = {
  id: string
  first_name: string
  last_name: string
  phone_number: string | null
}

export type AssignedVehicle = {
  id: string
  make: string
  model: string
  color: string
  license_plate: string
  category: VehicleCategory
}

export type Ride = {
  id: string
  rider_id: string
  driver_id: string | null
  vehicle_id: string | null
  driver: AssignedDriver | null
  vehicle: AssignedVehicle | null
  status: RideStatus
  ride_type: RideType
  pickup: Coordinates
  destination: Coordinates
  estimated_distance_km: string
  estimated_duration_minutes: string
  estimated_fare: string
  final_fare: string | null
  currency: string
  requested_at: string
  accepted_at: string | null
  arriving_at: string | null
  arrived_at: string | null
  started_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  created_at: string
  updated_at: string
}

export type AuthSession = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}
