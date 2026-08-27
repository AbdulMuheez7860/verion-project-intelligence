import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeAll, beforeEach } from 'vitest'
import { AnalyticsPage } from '@/features/analytics/analytics-page'
import type { AnalyticsOverview } from '@/types/api'

const buildingFixture: AnalyticsOverview = {
  baseline: {
    available: false,
    snapshotCount: 0,
    status: 'building',
    message: 'Analytics will appear after Verion completes its first repository analysis.',
  },
  freshness: {
    lastSnapshotAt: null,
    lastAnalysisAt: null,
    staleRepositories: [],
    neverAnalyzedRepositories: ['acme/api'],
  },
  healthTrend: [],
  securityTrend: [],
  qualityTrend: [],
  dependencyTrend: [],
  riskTrend: [],
  findingTrend: [],
  repositoryComparisons: [],
  regressions: [],
  improvements: [],
  repositoryOptions: [{ id: 'repo-1', name: 'acme/api', snapshotCount: 0 }],
  rangeDays: 90,
}

const trendingFixture: AnalyticsOverview = {
  baseline: {
    available: true,
    snapshotCount: 3,
    status: 'trending',
    firstCapturedAt: new Date('2026-02-01').toISOString(),
    lastCapturedAt: new Date('2026-03-01').toISOString(),
    message: 'Historical trends are computed from completed analysis snapshots.',
  },
  freshness: {
    lastSnapshotAt: new Date('2026-03-01').toISOString(),
    lastAnalysisAt: new Date('2026-03-01').toISOString(),
    staleRepositories: [],
    neverAnalyzedRepositories: [],
  },
  healthTrend: [
    { capturedAt: new Date('2026-02-01').toISOString(), value: 68 },
    { capturedAt: new Date('2026-02-15').toISOString(), value: 74 },
    { capturedAt: new Date('2026-03-01').toISOString(), value: 81 },
  ],
  securityTrend: [
    { capturedAt: new Date('2026-02-01').toISOString(), value: 70 },
    { capturedAt: new Date('2026-03-01').toISOString(), value: 85 },
  ],
  qualityTrend: [],
  dependencyTrend: [],
  riskTrend: [],
  findingTrend: [],
  repositoryComparisons: [
    {
      id: 'repo-1',
      name: 'acme/api',
      healthScore: 81,
      securityScore: 85,
      qualityScore: 78,
      dependencyScore: 90,
      prRiskScore: 35,
      trendDirection: 'improving',
      snapshotCount: 3,
      lastAnalyzedAt: new Date('2026-03-01').toISOString(),
    },
  ],
  regressions: [],
  improvements: [
    {
      metric: 'health_score',
      label: 'Health score',
      current: 81,
      previous: 68,
      delta: 13,
      direction: 'improved',
      interpretation: 'Increased by 13 points.',
      available: true,
      repositoryId: 'repo-1',
      repositoryName: 'acme/api',
    },
  ],
  repositoryOptions: [{ id: 'repo-1', name: 'acme/api', snapshotCount: 3 }],
  rangeDays: 90,
}

vi.mock('@/api/analytics', () => ({
  analyticsApi: {
    overview: vi.fn(),
  },
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}))

beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal('ResizeObserver', ResizeObserverMock)
})

import { analyticsApi } from '@/api/analytics'

describe('AnalyticsPage', () => {
  beforeEach(() => {
    vi.mocked(analyticsApi.overview).mockReset()
  })

  it('renders building baseline state', async () => {
    vi.mocked(analyticsApi.overview).mockResolvedValue(buildingFixture)
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Baseline status')).toBeInTheDocument()
    expect(screen.getByText('Building your baseline')).toBeInTheDocument()
    expect(screen.getByText('Analyze a repository')).toBeInTheDocument()
  })

  it('renders historical charts and improvements', async () => {
    vi.mocked(analyticsApi.overview).mockResolvedValue(trendingFixture)
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Historical trends available')).toBeInTheDocument()
    expect(screen.getByText('Engineering health over time')).toBeInTheDocument()
    expect(screen.getByText('Repository comparison')).toBeInTheDocument()
    expect(screen.getByText('Improvements')).toBeInTheDocument()
    expect(screen.getByText(/Health score in acme\/api/)).toBeInTheDocument()
  })
})
