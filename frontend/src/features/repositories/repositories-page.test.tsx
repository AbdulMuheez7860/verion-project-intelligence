import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { RepositoriesPage } from '@/features/repositories/repositories-page'
import type { PaginatedResponse, Repository } from '@/types/api'

const listMock = vi.fn()

vi.mock('@/api/repositories', () => ({
  repositoriesApi: {
    list: (...args: unknown[]) => listMock(...args),
  },
}))

vi.mock('@/api/integrations', () => ({
  integrationsApi: {
    getGitHub: vi.fn().mockResolvedValue({ status: 'connected' }),
  },
}))

const pageFixture: PaginatedResponse<Repository> = {
  items: [
    {
      id: 'repo-1',
      name: 'api',
      owner: 'acme',
      healthScore: 82,
      securityScore: 88,
      codeQualityScore: 75,
      openPullRequests: 2,
      riskLevel: 'low',
      analysisStatus: 'complete',
      lastAnalyzedAt: new Date().toISOString(),
      defaultBranch: 'main',
      private: false,
    },
  ],
  total: 1,
  page: 1,
  pageSize: 20,
  hasNext: false,
}

describe('RepositoriesPage', () => {
  beforeEach(() => {
    listMock.mockReset()
    listMock.mockResolvedValue(pageFixture)
  })

  it('renders repositories from paginated API', async () => {
    render(
      <MemoryRouter>
        <RepositoriesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('api')).toBeInTheDocument()
    expect(screen.getByText(/acme/)).toBeInTheDocument()
    expect(listMock).toHaveBeenCalled()
  })

  it('debounces search input into query params', async () => {
    render(
      <MemoryRouter>
        <RepositoriesPage />
      </MemoryRouter>,
    )

    await screen.findByText('api')
    const [searchInput] = screen.getAllByLabelText('Search repositories')
    fireEvent.change(searchInput, { target: { value: 'beta' } })

    await vi.waitFor(() => {
      expect(listMock).toHaveBeenCalledWith(expect.objectContaining({ q: 'beta' }))
    })
  })
})
