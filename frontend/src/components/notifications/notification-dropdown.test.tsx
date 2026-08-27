import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { NotificationDropdown } from '@/components/notifications/notification-dropdown'

vi.mock('@/api/notifications', () => ({
  notificationsApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 5, hasNext: false }),
    markRead: vi.fn(),
  },
}))
vi.mock('@/hooks/use-notifications', () => ({
  useUnreadNotificationCount: () => ({ count: 3, refresh: vi.fn() }),
}))
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ push: vi.fn() }) }))

describe('NotificationDropdown', () => {
  it('shows unread badge on trigger', () => {
    render(
      <MemoryRouter>
        <NotificationDropdown />
      </MemoryRouter>,
    )
    expect(screen.getByLabelText(/notifications, 3 unread/i)).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })
})
