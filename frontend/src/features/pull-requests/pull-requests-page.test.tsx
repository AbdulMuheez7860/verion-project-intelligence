import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { PullRequestsPage } from '@/features/pull-requests/pull-requests-page'
import type { PaginatedResponse, PullRequestListItem } from '@/types/api'

const listMock = vi.fn()

vi.mock('@/api/pull-requests', () => ({
  pullRequestsApi: {
    list: (...args: unknown[]) => listMock(...args),
  },
}))

const fixture: PaginatedResponse<PullRequestListItem> = {
  items: [
    {
      id: 900001,
      number: 42,
      repositoryId: 'repo-1',
      repositoryName: 'acme/api',
      title: 'Fix auth middleware',
      author: 'dev',
      status: 'open',
      draft: false,
      riskScore: 72,
      riskLevel: 'critical',
      verdict: 'critical_risk',
      verdictLabel: 'Critical risk',
      securityImpact: 2,
      qualityImpact: 1,
      dependencyImpact: 1,
      filesChanged: 5,
      issuesCount: 4,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      riskScoredAt: new Date().toISOString(),
    },
  ],
  total: 1,
  page: 1,
  pageSize: 20,
  hasNext: false,
}

describe('PullRequestsPage', () => {
  it('renders pull requests from paginated API', async () => {
    listMock.mockResolvedValue(fixture)
    render(
      <MemoryRouter>
        <PullRequestsPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/Fix auth middleware/i)).toBeInTheDocument()
    expect(screen.getByText('Critical risk')).toBeInTheDocument()
    expect(listMock).toHaveBeenCalled()
  })
})
