import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/layout/page-header'
import { cn } from '@/lib/utils'
import { usePermissions } from '@/hooks/use-permissions'
import type { Permission } from '@/types/api'

const settingsNav: { label: string; to: string; permission: Permission }[] = [
  { label: 'General', to: '/app/settings/general', permission: 'settings.read' },
  { label: 'Members & Access', to: '/app/settings/members', permission: 'members.read' },
  { label: 'Integrations', to: '/app/settings/integrations', permission: 'integrations.read' },
  { label: 'Analysis', to: '/app/settings/analysis', permission: 'analysis_settings.read' },
  { label: 'Notifications', to: '/app/settings/notifications', permission: 'notifications.preferences.update' },
  { label: 'Security', to: '/app/settings/security', permission: 'account.update' },
  { label: 'Audit Log', to: '/app/settings/audit-log', permission: 'audit.read' },
  { label: 'Account', to: '/app/settings/account', permission: 'account.update' },
]

export function SettingsLayout() {
  const { can } = usePermissions()
  const location = useLocation()
  const navigate = useNavigate()
  const visibleNav = settingsNav.filter((item) => can(item.permission))
  const activePath = visibleNav.find((item) => location.pathname.startsWith(item.to))?.to ?? visibleNav[0]?.to

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Manage your workspace and account configuration."
      />
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <div className="lg:hidden">
          <label htmlFor="settings-section" className="sr-only">
            Settings section
          </label>
          <select
            id="settings-section"
            className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
            value={activePath}
            onChange={(event) => navigate(event.target.value)}
          >
            {visibleNav.map((item) => (
              <option key={item.to} value={item.to}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        <nav className="hidden gap-1 lg:flex lg:flex-col" aria-label="Settings">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'whitespace-nowrap rounded-lg px-3 py-2 text-left text-xs font-medium',
                  isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <Outlet />
      </div>
    </div>
  )
}
