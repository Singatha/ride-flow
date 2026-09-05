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

export type AuthSession = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}
