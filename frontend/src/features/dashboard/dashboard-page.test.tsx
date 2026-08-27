import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { OverviewMetrics } from '@/components/dashboard/overview-metrics'
import { PullRequestIntelligenceSection } from '@/components/dashboard/pull-request-intelligence-section'
import type { DashboardSummaryResponse } from '@/types/api'

const summaryFixture: DashboardSummaryResponse = {
  generatedAt: new Date().toISOString(),
  hasActiveAnalysis: false,
  hasAnalysisData: true,
  overview: [
    {
      key: 'engineering_health',
      label: 'Engineering health',
      value: 82,
      definition: 'Composite health assessment.',
      href: '/app/dashboard',
      status: 'healthy',
    },
    {
      key: 'critical_findings',
      label: 'Critical findings',
      value: 2,
      definition: 'Critical findings.',
      href: '/app/security',
      status: 'critical',
    },
  ],
  health: {
    score: 82,
    level: 'low',
    definition: 'Composite health.',
    dimensions: [],
    factors: ['2 critical security findings open'],
  },
  attention: [],
  repositories: [],
  pullRequests: {
    highRisk: [
      {
        id: 42,
        repositoryId: 'repo-1',
        repositoryName: 'acme/api',
        title: 'Risky auth change',
        riskScore: 72,
        riskLevel: 'critical',
        verdict: 'critical_risk',
        verdictLabel: 'Critical risk',
        verdictReason: 'Risk score exceeds critical threshold.',
        status: 'open',
        issuesCount: 3,
      },
    ],
    awaitingAnalysis: [],
    recentlyAnalyzed: [],
  },
  security: {
    severityCounts: { critical: 2, high: 1, medium: 0, low: 0 },
    total: 3,
    hasData: true,
  },
  analysisActivity: [],
  riskDistribution: {
    buckets: [
      { key: 'critical', label: 'Critical', count: 2 },
      { key: 'high', label: 'High', count: 1 },
      { key: 'medium', label: 'Medium', count: 0 },
      { key: 'low', label: 'Low', count: 0 },
    ],
    total: 3,
    hasData: true,
  },
  trends: {
    available: false,
    message: 'Verion needs multiple completed analyses to establish engineering trends.',
    direction: 'unavailable',
    completedAnalysesCount: 1,
  },
  recommendedActions: [],
}

vi.mock('@/hooks/use-dashboard', () => ({
  useDashboardSummary: () => ({
    data: summaryFixture,
    status: 'success',
    error: null,
    requestId: null,
    isUnavailable: false,
    lastUpdated: new Date('2026-08-12T12:00:00Z'),
    isRefreshing: false,
    refetch: vi.fn(),
  }),
}))

describe('dashboard components', () => {
  it('renders overview metrics with values and links', () => {
    render(
      <MemoryRouter>
        <OverviewMetrics metrics={summaryFixture.overview} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Engineering health')).toBeInTheDocument()
    expect(screen.getByText('82')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /engineering health/i })).toHaveAttribute('href', '/app/dashboard')
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders PR risk verdict labels', () => {
    render(
      <MemoryRouter>
        <PullRequestIntelligenceSection pullRequests={summaryFixture.pullRequests} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Critical risk')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /#42 risky auth change/i })).toHaveAttribute(
      'href',
      '/app/pull-requests/42',
    )
  })
})

describe('DashboardPage', () => {
  it('renders dashboard sections from summary data', async () => {
    const { DashboardPage } = await import('@/features/dashboard/dashboard-page')
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Requires attention')).toBeInTheDocument()
    expect(screen.getByText('Repository health')).toBeInTheDocument()
    expect(screen.getByText('Building your baseline')).toBeInTheDocument()
    expect(screen.getAllByText('Critical risk').length).toBeGreaterThan(0)
  })
})
