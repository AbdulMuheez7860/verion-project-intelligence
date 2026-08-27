import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IntegrationsSettingsPage } from '@/features/integrations/integrations-settings-page'

vi.mock('@/api/integrations', () => ({
  integrationsApi: {
    getGitHub: vi.fn(),
    connectGitHub: vi.fn(),
    disconnectGitHub: vi.fn(),
  },
}))
vi.mock('@/hooks/use-permissions', () => ({
  usePermissions: () => ({
    can: (p: string) => p === 'integrations.read',
    role: 'viewer',
    isAdmin: false,
  }),
}))
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ push: vi.fn() }) }))

import { integrationsApi } from '@/api/integrations'

describe('IntegrationsSettingsPage', () => {
  beforeEach(() => {
    vi.mocked(integrationsApi.getGitHub).mockResolvedValue({
      status: 'connected',
      configured: true,
      githubLogin: 'acme-org',
      connectedRepositories: 3,
    })
  })

  it('hides disconnect for viewers', async () => {
    render(
      <MemoryRouter>
        <IntegrationsSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/connected as acme-org/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /disconnect/i })).not.toBeInTheDocument()
  })
})
