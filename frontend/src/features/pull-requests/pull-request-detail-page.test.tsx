import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { PullRequestDetailPage } from '@/features/pull-requests/pull-request-detail-page'
import type { PullRequestIntelligence } from '@/types/api'

const { intelligenceFixture } = vi.hoisted(() => {
  const fixture: PullRequestIntelligence = {
    id: 900001,
    number: 42,
    title: 'Fix auth middleware',
    repositoryId: 'repo-1',
    repositoryName: 'acme/api',
    author: 'dev',
    status: 'open',
    draft: false,
    createdAt: new Date().toISOString(),
    mergeSafety: {
      key: 'critical_risk',
      label: 'BLOCKED',
      headline: 'Critical risk',
      explanation: 'Risk score exceeds critical threshold.',
      riskScore: 72,
      riskLevel: 'critical',
    },
    freshness: {
      status: 'current',
      label: 'Analysis complete',
      isStale: false,
      riskScoredAt: new Date().toISOString(),
    },
    riskScoreDetail: {
      value: 72,
      level: 'critical',
      engine: 'Verion Risk Engine',
      factors: [
        {
          label: 'Security findings',
          contribution: 25,
          explanation: '2 finding(s) in this change (1 high, 1 medium).',
        },
      ],
    },
    securitySummary: { critical: 1, high: 1, medium: 0, low: 0 },
    securityFindings: [],
    qualityFindings: [],
    dependencyFindings: [],
    impactCounts: { security: 2, quality: 1, dependency: 1, total: 4 },
    changedFiles: [{ path: 'app/auth.py', status: 'modified', additions: 10, deletions: 2, category: 'security' }],
    affectedAreas: [{ key: 'authentication', label: 'Authentication', fileCount: 1, findingCount: 1 }],
    analysis: { status: 'complete', repositoryAnalysisStatus: 'complete' },
    recommendations: [
      {
        id: 'critical-security',
        label: 'Review critical security findings',
        description: '1 critical security finding affects changed files.',
        priority: 'high',
      },
    ],
  }
  return { intelligenceFixture: fixture }
})

vi.mock('@/api/pull-requests', () => ({
  pullRequestsApi: {
    getIntelligence: vi.fn().mockResolvedValue(intelligenceFixture),
    reanalyze: vi.fn(),
  },
}))

describe('PullRequestDetailPage', () => {
  it('renders merge safety and risk breakdown', async () => {
    render(
      <MemoryRouter initialEntries={['/app/pull-requests/900001']}>
        <Routes>
          <Route path="/app/pull-requests/:id" element={<PullRequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('BLOCKED')).toBeInTheDocument()
    expect(screen.getByText('Security findings')).toBeInTheDocument()
    expect(screen.getByText('Recommended review actions')).toBeInTheDocument()
  })
})
