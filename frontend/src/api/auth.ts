import { authService, type LoginPayload, type SignupPayload } from '@/api/authService'

export type { LoginPayload, SignupPayload }

/** @deprecated Use authService instead */
export const authApi = {
  me: () => authService.me(),
  login: (payload: LoginPayload) => authService.login(payload),
  signup: (payload: SignupPayload) => authService.signup(payload),
  logout: () => authService.logout(),
  forgotPassword: (email: string) => authService.forgotPassword(email),
  resetPassword: (password: string, token: string) => authService.resetPassword(password, token),
}

export { authService }
