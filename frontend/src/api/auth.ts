import { apiRequest } from './client'
import type { AuthSession, User, UserRole } from './types'

export type LoginInput = {
  email: string
  password: string
}

export type RegisterInput = LoginInput & {
  role: Exclude<UserRole, 'ADMIN'>
  first_name: string
  last_name: string
  phone_number?: string
}

export type UpdateProfileInput = {
  first_name?: string
  last_name?: string
  phone_number?: string | null
}

export function login(input: LoginInput) {
  return apiRequest<AuthSession>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function register(input: RegisterInput) {
  return apiRequest<AuthSession>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function refreshSession() {
  return apiRequest<AuthSession>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function logout() {
  return apiRequest<void>('/auth/logout', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function getProfile(accessToken: string) {
  return apiRequest<User>('/users/me', { accessToken })
}

export function updateProfile(accessToken: string, input: UpdateProfileInput) {
  return apiRequest<User>('/users/me', {
    method: 'PATCH',
    accessToken,
    body: JSON.stringify(input),
  })
}
