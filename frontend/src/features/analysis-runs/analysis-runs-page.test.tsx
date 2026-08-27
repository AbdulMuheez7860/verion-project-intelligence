import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { AnalysisRunsPage } from '@/features/analysis-runs/analysis-runs-page'
import type { AnalysisRun, PaginatedResponse, Repository } from '@/types/api'

const runsFixture: PaginatedResponse<AnalysisRun> = {
  items: [
    {
      id: 'run-1',
      repositoryId: 'repo-1',
      repositoryName: 'acme/api',
      status: 'complete',
      trigger: 'manual',
      commitSha: 'abc1234',
      findingCount: 5,
      healthScore: 82,
      durationSeconds: 120,
      startedAt: new Date('2026-03-01').toISOString(),
    },
  ],
  page: 1,
  pageSize: 20,
  total: 1,
  hasNext: false,
}

const reposFixture: PaginatedResponse<Repository> = {
  items: [{ id: 'repo-1', name: 'api', owner: 'acme', fullName: 'acme/api' } as Repository],
  page: 1,
  pageSize: 100,
  total: 1,
  hasNext: false,
}

vi.mock('@/api/analysis-runs', () => ({
  analysisRunsApi: { list: vi.fn() },
}))

vi.mock('@/api/repositories', () => ({
  repositoriesApi: { list: vi.fn() },
}))

import { analysisRunsApi } from '@/api/analysis-runs'
import { repositoriesApi } from '@/api/repositories'

describe('AnalysisRunsPage', () => {
  beforeEach(() => {
    vi.mocked(analysisRunsApi.list).mockResolvedValue(runsFixture)
    vi.mocked(repositoriesApi.list).mockResolvedValue(reposFixture)
  })

  it('renders analysis runs list', async () => {
    render(
      <MemoryRouter>
        <AnalysisRunsPage />
      </MemoryRouter>,
    )
    expect((await screen.findAllByText('acme/api')).length).toBeGreaterThan(0)
    expect(screen.getByText('complete')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'acme/api' })).toHaveAttribute('href', '/app/analysis-runs/run-1')
  })

  it('renders empty state', async () => {
    vi.mocked(analysisRunsApi.list).mockResolvedValue({ ...runsFixture, items: [], total: 0 })
    render(
      <MemoryRouter>
        <AnalysisRunsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('No analysis runs')).toBeInTheDocument()
  })
})
