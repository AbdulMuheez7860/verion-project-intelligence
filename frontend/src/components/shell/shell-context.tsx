import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

interface ShellContextValue {
  mobileNavOpen: boolean
  setMobileNavOpen: (open: boolean) => void
  sidebarCollapsed: boolean
  toggleSidebarCollapsed: () => void
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
}

const ShellContext = createContext<ShellContextValue | null>(null)

const SIDEBAR_COLLAPSED_KEY = 'verion-sidebar-collapsed'

export function ShellProvider({ children }: { children: ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
  })
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed ? 'true' : 'false')
  }, [sidebarCollapsed])

  const value = useMemo(
    () => ({
      mobileNavOpen,
      setMobileNavOpen,
      sidebarCollapsed,
      toggleSidebarCollapsed: () => setSidebarCollapsed((current) => !current),
      commandPaletteOpen,
      setCommandPaletteOpen,
    }),
    [mobileNavOpen, sidebarCollapsed, commandPaletteOpen],
  )

  return <ShellContext.Provider value={value}>{children}</ShellContext.Provider>
}

export function useShell() {
  const context = useContext(ShellContext)
  if (!context) {
    throw new Error('useShell must be used within ShellProvider')
  }
  return context
}
