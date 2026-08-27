import { useNavigate } from 'react-router-dom'
import { LogOut, Menu, Moon, Search, Settings, Sun, User } from 'lucide-react'
import { Breadcrumbs } from '@/components/navigation/breadcrumbs'
import { NotificationDropdown } from '@/components/notifications/notification-dropdown'
import { useShell } from '@/components/shell/shell-context'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/use-auth'
import { useTheme } from '@/hooks/use-theme'
import { cn } from '@/lib/utils'

export function Topbar() {
  const { user, organization, logout } = useAuth()
  const navigate = useNavigate()
  const { setMobileNavOpen, setCommandPaletteOpen, sidebarCollapsed } = useShell()
  const { dark, toggle } = useTheme()

  const initials = user?.name
    ?.split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex h-14 items-center justify-between gap-3 px-4 md:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileNavOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="size-4" />
          </Button>
          <Breadcrumbs />
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="secondary"
            size="sm"
            className="hidden h-9 w-56 justify-between px-3 text-muted-foreground sm:inline-flex"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open command palette"
          >
            <span className="flex items-center gap-2">
              <Search className="size-3.5" aria-hidden="true" />
              <span>Search</span>
            </span>
            <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              ⌘K
            </kbd>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="sm:hidden"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open command palette"
          >
            <Search className="size-4" />
          </Button>

          <Button variant="ghost" size="icon" onClick={toggle} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}>
            <Sun className="size-4 dark:hidden" />
            <Moon className="hidden size-4 dark:block" />
          </Button>

          <NotificationDropdown />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="ml-1 flex items-center gap-2 rounded-md border border-border bg-card px-2 py-1.5 text-left transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Open user menu"
              >
                <div className="grid size-7 place-items-center rounded-md bg-primary/10 font-mono text-[10px] font-semibold text-primary">
                  {initials ?? 'U'}
                </div>
                <div className="hidden min-w-0 sm:block">
                  <p className="truncate text-xs font-medium leading-none">{user?.name ?? 'User'}</p>
                  <p className="mt-1 truncate text-[11px] text-muted-foreground">{organization?.name ?? 'Workspace'}</p>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <p className="text-sm font-medium">{user?.name}</p>
                <p className="text-metadata">{user?.email}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/app/settings/account')}>
                <User className="size-4" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/settings/general')}>
                <Settings className="size-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => void handleLogout()}>
                <LogOut className="size-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <div
        className={cn(
          'hidden border-t border-border/60 px-6 py-2 text-metadata md:block',
          sidebarCollapsed ? 'md:pl-[calc(4.5rem+1.5rem)]' : 'md:pl-[calc(15rem+1.5rem)]',
        )}
      >
        Engineering intelligence workspace
      </div>
    </header>
  )
}
