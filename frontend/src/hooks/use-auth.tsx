import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { isApiError, isNetworkError } from '@/api/client'
import { authService } from '@/api/authService'
import type { Membership, Organization, Session, User } from '@/types/api'

interface AuthContextValue {
  user: User | null
  organization: Organization | null
  membership: Membership | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (payload: {
    name: string
    email: string
    team: string
    password: string
  }) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function applySession(
  session: Session,
  setters: {
    setUser: (user: User) => void
    setOrganization: (organization: Organization) => void
    setMembership: (membership: Membership) => void
  },
) {
  setters.setUser(session.user)
  setters.setOrganization(session.organization)
  setters.setMembership(session.membership)
}

function clearSession(setters: {
  setUser: (user: User | null) => void
  setOrganization: (organization: Organization | null) => void
  setMembership: (membership: Membership | null) => void
}) {
  setters.setUser(null)
  setters.setOrganization(null)
  setters.setMembership(null)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [organization, setOrganization] = useState<Organization | null>(null)
  const [membership, setMembership] = useState<Membership | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const sessionSetters = useMemo(
    () => ({ setUser, setOrganization, setMembership }),
    [],
  )

  const refresh = useCallback(async () => {
    setIsLoading(true)
    try {
      const session = await authService.refresh()
      applySession(session, sessionSetters)
    } catch (refreshError) {
      if (isNetworkError(refreshError)) {
        clearSession(sessionSetters)
        return
      }

      try {
        const session = await authService.me()
        applySession(session, sessionSetters)
      } catch (error) {
        if (
          isNetworkError(error) ||
          (isApiError(error) && (error.status === 401 || error.status === 403))
        ) {
          clearSession(sessionSetters)
        } else {
          clearSession(sessionSetters)
        }
      }
    } finally {
      setIsLoading(false)
    }
  }, [sessionSetters])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      const session = await authService.login({ email, password })
      applySession(session, sessionSetters)
    },
    [sessionSetters],
  )

  const signup = useCallback(
    async (payload: { name: string; email: string; team: string; password: string }) => {
      const session = await authService.signup(payload)
      applySession(session, sessionSetters)
    },
    [sessionSetters],
  )

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      clearSession(sessionSetters)
    }
  }, [sessionSetters])

  const value = useMemo(
    () => ({
      user,
      organization,
      membership,
      isLoading,
      isAuthenticated: Boolean(user),
      login,
      signup,
      logout,
      refresh,
    }),
    [user, organization, membership, isLoading, login, signup, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
