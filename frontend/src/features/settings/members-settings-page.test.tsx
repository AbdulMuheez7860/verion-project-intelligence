import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MembersSettingsPage } from '@/features/settings/members-settings-page'
import type { Invitation, Member } from '@/types/api'

const membersFixture: Member[] = [
  {
    id: 'm-1',
    userId: 'u-1',
    name: 'Ada Lovelace',
    email: 'ada@acme.dev',
    role: 'owner',
    joinedAt: new Date('2026-01-01').toISOString(),
    status: 'active',
    isCurrentUser: true,
  },
  {
    id: 'm-2',
    userId: 'u-2',
    name: 'Grace Hopper',
    email: 'grace@acme.dev',
    role: 'member',
    joinedAt: new Date('2026-02-01').toISOString(),
    status: 'active',
    isCurrentUser: false,
  },
]

vi.mock('@/api/organization', () => ({
  organizationApi: {
    members: vi.fn(),
    invitations: vi.fn(),
    createInvitation: vi.fn(),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn(),
    revokeInvitation: vi.fn(),
  },
}))
vi.mock('@/hooks/use-permissions', () => ({
  usePermissions: () => ({
    can: (p: string) => ['members.read', 'members.invite', 'members.update_role', 'members.remove'].includes(p),
    role: 'owner',
    isAdmin: true,
  }),
}))
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ push: vi.fn() }) }))

import { organizationApi } from '@/api/organization'

describe('MembersSettingsPage', () => {
  beforeEach(() => {
    vi.mocked(organizationApi.members).mockResolvedValue({
      items: membersFixture,
      total: 2,
      page: 1,
      pageSize: 50,
      hasNext: false,
    })
    vi.mocked(organizationApi.invitations).mockResolvedValue([] as Invitation[])
  })

  it('renders member table with current user indicator', async () => {
    render(
      <MemoryRouter>
        <MembersSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Ada Lovelace (you)')).toBeInTheDocument()
    expect(screen.getByText('Grace Hopper')).toBeInTheDocument()
  })

  it('shows invite member action for admins', async () => {
    render(
      <MemoryRouter>
        <MembersSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('button', { name: /invite member/i })).toBeInTheDocument()
  })
})
