import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { NotificationsSettingsPage } from '@/features/settings/notifications-settings-page'

vi.mock('@/api/notifications', () => ({
  notificationsApi: {
    preferences: vi.fn().mockResolvedValue({
      securityAlerts: true,
      dependencyAlerts: true,
      prRiskAlerts: true,
      analysisAlerts: true,
      regressionAlerts: false,
      workspaceAlerts: true,
    }),
    updatePreferences: vi.fn(),
  },
}))
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ push: vi.fn() }) }))

describe('NotificationsSettingsPage', () => {
  it('renders preference toggles', async () => {
    render(
      <MemoryRouter>
        <NotificationsSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Security alerts')).toBeInTheDocument()
    expect(screen.getByText(/email delivery is not configured/i)).toBeInTheDocument()
  })
})
