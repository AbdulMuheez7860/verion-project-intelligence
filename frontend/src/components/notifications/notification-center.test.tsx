import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationCenterPanel } from '@/components/notifications/notification-center'
import type { Notification } from '@/types/api'

vi.mock('@/api/notifications', () => ({
  notificationsApi: {
    list: vi.fn(),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
    unreadCount: vi.fn(),
  },
}))
vi.mock('@/hooks/use-notifications', () => ({
  useNotifications: vi.fn(),
  useUnreadNotificationCount: () => ({ count: 1, refresh: vi.fn() }),
}))
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ push: vi.fn() }) }))

import { useNotifications } from '@/hooks/use-notifications'

const notificationFixture: Notification = {
  id: 'n-1',
  type: 'security.critical_finding',
  severity: 'critical',
  title: 'Critical security finding detected',
  body: 'payment-service has 2 critical findings.',
  href: '/app/security',
  repositoryName: 'payment-service',
  read: false,
  createdAt: new Date().toISOString(),
}

describe('NotificationCenterPanel', () => {
  beforeEach(() => {
    vi.mocked(useNotifications).mockReturnValue({
      data: {
        items: [notificationFixture],
        total: 1,
        page: 1,
        pageSize: 20,
        hasNext: false,
      },
      status: 'success',
      reload: vi.fn(),
    })
  })

  it('renders notification with context and severity', async () => {
    render(
      <MemoryRouter>
        <NotificationCenterPanel />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Critical security finding detected')).toBeInTheDocument()
    expect(screen.getByText(/payment-service has 2 critical findings/i)).toBeInTheDocument()
    expect(screen.getByText('Unread')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view details/i })).toHaveAttribute('href', '/app/security')
  })
})
