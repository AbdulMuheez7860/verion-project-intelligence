import { apiRequest } from '@/api/client'
import type { Session } from '@/types/api'

export interface LoginPayload {
  email: string
  password: string
}

export interface SignupPayload {
  name: string
  email: string
  team: string
  password: string
}

export const authService = {
  me: () => apiRequest<Session>('/api/v1/auth/me'),

  refresh: () => apiRequest<Session>('/api/v1/auth/refresh', { method: 'POST' }),

  login: (payload: LoginPayload) =>
    apiRequest<Session>('/api/v1/auth/login', { method: 'POST', body: payload }),

  signup: (payload: SignupPayload) =>
    apiRequest<Session>('/api/v1/auth/signup', { method: 'POST', body: payload }),

  logout: () => apiRequest<void>('/api/v1/auth/logout', { method: 'POST' }),

  forgotPassword: (email: string) =>
    apiRequest<void>('/api/v1/auth/forgot-password', { method: 'POST', body: { email } }),

  resetPassword: (password: string, token: string) =>
    apiRequest<void>('/api/v1/auth/reset-password', {
      method: 'POST',
      body: { password, token },
    }),

  updateProfile: (payload: { name?: string; timezone?: string }) =>
    apiRequest<Session>('/api/v1/auth/me', { method: 'PATCH', body: payload }),

  changePassword: (payload: { currentPassword: string; newPassword: string }) =>
    apiRequest<void>('/api/v1/auth/change-password', {
      method: 'POST',
      body: {
        currentPassword: payload.currentPassword,
        newPassword: payload.newPassword,
      },
    }),
}
