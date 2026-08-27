export interface DemoSession {
  authenticated: true
  userId: string
  name: string
  email: string
}

export interface AuthAdapter {
  login(email: string, password: string): Promise<DemoSession>
  signup(input: { name: string; email: string; team: string; password: string }): Promise<DemoSession>
  logout(): Promise<void>
  getSession(): DemoSession | null
  isAuthenticated(): boolean
}
