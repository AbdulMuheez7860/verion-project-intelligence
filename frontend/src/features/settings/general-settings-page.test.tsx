import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { GeneralSettingsPage } from '@/features/settings/general-settings-page'
import type { OrganizationOverview } from '@/types/api'

const overviewFixture: OrganizationOverview = {
  id: 'org-1',
  name: 'Acme Platform',
  slug: 'acme-platform',
  createdAt: new Date('2026-01-01').toISOString(),
  currentUserRole: 'owner',
  repositoryCount: 2,
  memberCount: 1,
}

vi.mock('@/api/organization', () => ({ organizationApi: { overview: vi.fn(), update: vi.fn() } }))
vi.mock('@/hooks/use-permissions', () => ({
  usePermissions: () => ({
    can: (p: string) => p === 'settings.read' || p === 'settings.update',
    role: 'owner',
    isAdmin: true,
  }),
}))
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ push: vi.fn() }) }))

import { organizationApi } from '@/api/organization'

describe('GeneralSettingsPage', () => {
  beforeEach(() => {
    vi.mocked(organizationApi.overview).mockResolvedValue(overviewFixture)
  })

  it('renders organization overview', async () => {
    render(
      <MemoryRouter>
        <GeneralSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('General')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Acme Platform')).toBeInTheDocument()
    expect(screen.getByText('acme-platform')).toBeInTheDocument()
  })
})
