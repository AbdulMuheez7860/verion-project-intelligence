import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { RepositoryDetailPage } from '@/features/repositories/repository-detail-page'
import type { RepositoryIntelligence } from '@/types/api'

const intelligenceFixture: RepositoryIntelligence = {
  repository: {
    id: 'repo-1',
    name: 'api',
    owner: 'acme',
    openPullRequests: 1,
    analysisStatus: 'complete',
    lastAnalyzedAt: new Date().toISOString(),
    healthScore: 80,
    securityScore: 85,
    codeQualityScore: 78,
    riskLevel: 'low',
    defaultBranch: 'main',
    htmlUrl: 'https://github.com/acme/api',
  },
  health: {
    healthScore: 80,
    securityScore: 85,
    codeQualityScore: 78,
    dependencyScore: 90,
    hasCompletedAnalysis: true,
    healthDefinition: 'Composite health.',
    securityDefinition: 'Security score.',
    qualityDefinition: 'Quality score.',
    dependencyDefinition: 'Dependency health.',
    prRiskDefinition: 'PR risk average.',
  },
  connection: {
    githubStatus: 'connected',
    canAnalyze: true,
  },
  latestAnalysis: {
    id: 'run-1',
    repositoryId: 'repo-1',
    status: 'complete',
    trigger: 'manual',
    findingCount: 3,
    commitSha: 'abc123',
    branch: 'main',
    durationSeconds: 120,
  },
  securitySummary: {
    hasAnalysisData: true,
    severityCounts: { critical: 0, high: 1, medium: 1, low: 1 },
  },
  qualitySummary: { hasAnalysisData: true, score: 78 },
  dependencySummary: { hasAnalysisData: true, totalPackages: 2, outdatedCount: 0, vulnerableCount: 0, abandonedCount: 0 },
  recommendedActions: [],
}

vi.mock('@/hooks/use-repository-intelligence', () => ({
  useRepositoryIntelligence: () => ({
    data: intelligenceFixture,
    status: 'success',
    error: null,
    refetch: vi.fn(),
    isAnalyzing: false,
  }),
}))

vi.mock('@/api/repositories', () => ({
  repositoriesApi: {
    listFindings: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 8, hasNext: false }),
    listDependencies: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 8, hasNext: false }),
    listPullRequests: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 8, hasNext: false }),
    listAnalysisRuns: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 8, hasNext: false }),
    getHealthHistory: vi.fn().mockResolvedValue({ points: [], hasSufficientHistory: false, message: 'Baseline' }),
    analyze: vi.fn(),
  },
}))

describe('RepositoryDetailPage', () => {
  it('shows health overview and analysis status', async () => {
    render(
      <MemoryRouter initialEntries={['/app/repositories/repo-1']}>
        <Routes>
          <Route path="/app/repositories/:id" element={<RepositoryDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'api' })).toBeInTheDocument()
    expect(screen.getByText('Health overview')).toBeInTheDocument()
    expect(screen.getByText('Analysis status')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Analyze repository/i })).toBeEnabled()
  })
})
