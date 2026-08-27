import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { CommandPalette } from '@/components/command-palette/command-palette'
import { Sidebar } from '@/components/navigation/sidebar'
import { Topbar } from '@/components/navigation/topbar'
import { ShellProvider, useShell } from '@/components/shell/shell-context'
import { cn } from '@/lib/utils'

function AppShellContent() {
  const { sidebarCollapsed, setCommandPaletteOpen } = useShell()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [setCommandPaletteOpen])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Sidebar />
      <div
        className={cn(
          'transition-[padding] duration-200',
          sidebarCollapsed ? 'md:pl-[4.5rem]' : 'md:pl-60',
        )}
      >
        <Topbar />
        <main id="main-content" className="mx-auto max-w-[1440px] px-4 py-5 md:px-6 md:py-6">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  )
}

export function AppShell() {
  return (
    <ShellProvider>
      <AppShellContent />
    </ShellProvider>
  )
}
