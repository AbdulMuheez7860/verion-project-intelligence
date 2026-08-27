import { NavLink } from 'react-router-dom'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { navGroups } from '@/components/navigation/nav-config'
import { LogoLink } from '@/components/navigation/logo'
import { WorkspaceSelector } from '@/components/navigation/workspace-selector'
import { useShell } from '@/components/shell/shell-context'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const { mobileNavOpen, setMobileNavOpen, sidebarCollapsed, toggleSidebarCollapsed } = useShell()

  return (
    <>
      <div
        className={cn(
          'fixed inset-0 z-40 bg-foreground/25 transition-opacity md:hidden',
          mobileNavOpen ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={() => setMobileNavOpen(false)}
        aria-hidden="true"
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-sidebar-border bg-sidebar transition-[width,transform] duration-200 md:translate-x-0',
          mobileNavOpen ? 'translate-x-0' : '-translate-x-full',
          sidebarCollapsed ? 'w-[4.5rem]' : 'w-60',
        )}
        aria-label="Application navigation"
      >
        <div className={cn('flex items-center gap-2 px-3 py-4', sidebarCollapsed ? 'justify-center' : 'justify-between')}>
          <LogoLink compact={sidebarCollapsed} onClick={() => setMobileNavOpen(false)} />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation"
          >
            <X className="size-4" />
          </Button>
        </div>

        <div className={cn('px-3', sidebarCollapsed && 'px-2')}>
          <WorkspaceSelector collapsed={sidebarCollapsed} />
        </div>

        <Separator className="my-3 bg-sidebar-border" />

        <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-2 pb-4">
          {navGroups.map((group) => (
            <div key={group.label}>
              {!sidebarCollapsed ? (
                <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                  {group.label}
                </p>
              ) : null}
              <ul className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        onClick={() => setMobileNavOpen(false)}
                        title={sidebarCollapsed ? item.label : undefined}
                        className={({ isActive }) =>
                          cn(
                            'group flex items-center rounded-md border-l-2 py-2 text-sm transition-colors',
                            sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-2.5',
                            isActive
                              ? 'border-primary bg-sidebar-accent font-medium text-sidebar-accent-foreground'
                              : 'border-transparent text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground',
                          )
                        }
                      >
                        <Icon className="size-4 shrink-0" aria-hidden="true" />
                        {!sidebarCollapsed ? <span>{item.label}</span> : null}
                      </NavLink>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="hidden border-t border-sidebar-border p-2 md:block">
          <Button
            type="button"
            variant="ghost"
            size={sidebarCollapsed ? 'icon' : 'sm'}
            className={cn('w-full', !sidebarCollapsed && 'justify-start')}
            onClick={toggleSidebarCollapsed}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
            {!sidebarCollapsed ? <span>Collapse</span> : null}
          </Button>
        </div>
      </aside>
    </>
  )
}
