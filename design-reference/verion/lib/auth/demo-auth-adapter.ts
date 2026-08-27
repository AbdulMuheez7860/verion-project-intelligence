import type { AuthAdapter, DemoSession } from './auth-adapter'

const STORAGE_KEY = 'verion-demo-session'
const demoSession: DemoSession = { authenticated: true, userId: 'demo-user', name: 'Demo User', email: 'demo@verion.dev' }

export const demoAuthAdapter: AuthAdapter = {
  async login(email, password) {
    if (!email || password.length < 8) throw new Error('Invalid demo credentials. Use any valid email and an 8+ character password.')
    if (typeof window !== 'undefined') localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...demoSession, email }))
    return { ...demoSession, email }
  },
  async signup(input) {
    if (typeof window !== 'undefined') localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...demoSession, name: input.name, email: input.email }))
    return { ...demoSession, name: input.name, email: input.email }
  },
  async logout() { if (typeof window !== 'undefined') localStorage.removeItem(STORAGE_KEY) },
  getSession() {
    if (typeof window === 'undefined') return null
    try { const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') as DemoSession | null; return value?.authenticated ? value : null } catch { return null }
  },
  isAuthenticated() { return Boolean(this.getSession()) },
}
