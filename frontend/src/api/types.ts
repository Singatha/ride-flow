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
export type AuthSession = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}
