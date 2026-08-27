import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePermissions } from '@/hooks/use-permissions'
import type { MembershipRole } from '@/types/api'

const authMock = vi.hoisted(() => ({
  membership: { role: 'viewer' as MembershipRole },
}))

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => authMock,
}))

describe('usePermissions', () => {
  beforeEach(() => {
    authMock.membership = { role: 'viewer' }
  })

  it('grants read-only permissions to viewers', () => {
    const { result } = renderHook(() => usePermissions())
    expect(result.current.can('settings.read')).toBe(true)
    expect(result.current.can('members.invite')).toBe(false)
    expect(result.current.can('audit.read')).toBe(false)
  })

  it('denies admin mutations to members', () => {
    authMock.membership = { role: 'member' }
    const { result } = renderHook(() => usePermissions())
    expect(result.current.can('members.read')).toBe(true)
    expect(result.current.can('members.update_role')).toBe(false)
    expect(result.current.can('integrations.manage')).toBe(false)
  })

  it('grants admin permissions to owners', () => {
    authMock.membership = { role: 'owner' }
    const { result } = renderHook(() => usePermissions())
    expect(result.current.can('members.update_role')).toBe(true)
    expect(result.current.can('audit.read')).toBe(true)
    expect(result.current.isAdmin).toBe(true)
  })
})
