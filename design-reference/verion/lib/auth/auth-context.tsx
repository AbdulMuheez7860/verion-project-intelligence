'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { demoAuthAdapter } from './demo-auth-adapter'
import type { DemoSession } from './auth-adapter'

const AuthContext = createContext<{ session: DemoSession | null; ready: boolean; refresh: () => void }>({ session: null, ready: false, refresh: () => undefined })
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<DemoSession | null>(null)
  const [ready, setReady] = useState(false)
  const refresh = () => setSession(demoAuthAdapter.getSession())
  useEffect(() => { queueMicrotask(() => { refresh(); setReady(true) }) }, [])
  return <AuthContext.Provider value={{ session, ready, refresh }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)
