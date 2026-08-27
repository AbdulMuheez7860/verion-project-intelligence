import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuditLogSettingsPage } from '@/features/settings/audit-log-settings-page'

vi.mock('@/api/organization', () => ({
  auditLogsApi: { list: vi.fn() },
}))

import { auditLogsApi } from '@/api/organization'

describe('AuditLogSettingsPage', () => {
  beforeEach(() => {
    vi.mocked(auditLogsApi.list).mockResolvedValue({
      items: [
        {
          id: 'log-1',
          action: 'member.role_changed',
          actorUserId: 'u-1',
          actorName: 'Admin User',
          resourceType: 'member',
          resourceId: 'm-2',
          metadata: { previous_role: 'viewer', new_role: 'member' },
          createdAt: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      pageSize: 20,
      hasNext: false,
    })
  })

  it('renders audit events from API', async () => {
    render(
      <MemoryRouter>
        <AuditLogSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('member.role_changed')).toBeInTheDocument()
    expect(screen.getByText('Admin User')).toBeInTheDocument()
  })
})
