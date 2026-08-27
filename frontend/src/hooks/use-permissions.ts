import { useAuth } from '@/hooks/use-auth'
import type { MembershipRole, Permission } from '@/types/api'

const VIEWER: Permission[] = [
  'settings.read',
  'members.read',
  'integrations.read',
  'analysis_settings.read',
  'account.update',
  'notifications.read',
  'notifications.preferences.update',
]

const MEMBER: Permission[] = [...VIEWER]

const ADMIN: Permission[] = [
  ...MEMBER,
  'settings.update',
  'members.invite',
  'members.update_role',
  'members.remove',
  'integrations.manage',
  'audit.read',
]

const ROLE_PERMISSIONS: Record<MembershipRole, Permission[]> = {
  viewer: VIEWER,
  member: MEMBER,
  admin: ADMIN,
  owner: ADMIN,
}

const MEMBER_ROLES: MembershipRole[] = ['owner', 'admin', 'member']

export function usePermissions() {
  const { membership } = useAuth()
  const role = membership?.role ?? 'viewer'
  const permissions = ROLE_PERMISSIONS[role] ?? VIEWER

  const can = (permission: Permission) => permissions.includes(permission)

  return {
    role,
    can,
    canAnalyze: MEMBER_ROLES.includes(role),
    canRetry: MEMBER_ROLES.includes(role),
    canCancel: MEMBER_ROLES.includes(role),
    isViewer: role === 'viewer',
    isAdmin: role === 'admin' || role === 'owner',
  }
}
