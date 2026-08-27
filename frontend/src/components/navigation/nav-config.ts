import {
  Box,
  GitPullRequest,
  History,
  LayoutDashboard,
  LineChart,
  Package,
  Settings as SettingsIcon,
  ShieldCheck,
  Code2,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  description?: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export const navGroups: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      {
        label: 'Dashboard',
        to: '/app/dashboard',
        icon: LayoutDashboard,
        description: 'Engineering health overview',
      },
    ],
  },
  {
    label: 'Engineering',
    items: [
      { label: 'Repositories', to: '/app/repositories', icon: Box, description: 'Connected codebases' },
      { label: 'Analysis runs', to: '/app/analysis-runs', icon: History, description: 'Analysis execution history' },
      { label: 'Pull Requests', to: '/app/pull-requests', icon: GitPullRequest, description: 'PR risk and review' },
      { label: 'Security', to: '/app/security', icon: ShieldCheck, description: 'Security findings' },
      { label: 'Code Quality', to: '/app/code-quality', icon: Code2, description: 'Quality findings' },
      { label: 'Dependencies', to: '/app/dependencies', icon: Package, description: 'Package risk' },
      { label: 'Analytics', to: '/app/analytics', icon: LineChart, description: 'Engineering metrics' },
    ],
  },
  {
    label: 'Administration',
    items: [
      { label: 'Settings', to: '/app/settings', icon: SettingsIcon, description: 'Workspace configuration' },
    ],
  },
]

export const allNavItems = navGroups.flatMap((group) => group.items)

export function getNavItemForPath(pathname: string): NavItem | undefined {
  return allNavItems.find((item) => pathname === item.to || pathname.startsWith(`${item.to}/`))
}
