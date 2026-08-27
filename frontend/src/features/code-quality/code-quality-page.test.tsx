import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { CodeQualityPage } from '@/features/code-quality/code-quality-page'
import type { PaginatedResponse, QualityFinding, QualityIntelligence } from '@/types/api'

const { intelligenceFixture, findingsFixture } = vi.hoisted(() => {
  const intelligence: QualityIntelligence = {
    score: 62,
    severityCounts: { critical: 0, high: 1, medium: 1, low: 1 },
    hasAnalysisData: true,
    posture: {
      label: 'ELEVATED DEBT',
      level: 'high',
      explanation: '1 high-severity quality finding detected.',
    },
    freshness: {
      status: 'current',
      label: 'Analysis current',
      isStale: false,
      lastAnalyzedAt: new Date().toISOString(),
      analysisRunning: false,
    },
    totals: { open: 3, total: 3, repositoriesAffected: 1, connectedRepositories: 1, critical: 0, high: 1 },
    scannerCoverage: {
      executed: ['ruff', 'eslint'],
      supported: ['ruff', 'eslint'],
      hasData: true,
      note: 'Coverage reflects Ruff and ESLint execution.',
    },
    repositories: [
      {
        id: 'repo-1',
        name: 'acme/web',
        findingCount: 3,
        openCount: 3,
        highestSeverity: 'high',
        qualityScore: 62,
        analysisStatus: 'complete',
        lastAnalyzedAt: new Date().toISOString(),
      },
    ],
    topRules: [
      {
        ruleId: 'RUF001',
        analyzer: 'ruff',
        count: 2,
        highestSeverity: 'high',
        repositoryCount: 1,
      },
    ],
    unavailableMetrics: [
      { key: 'coverage', label: 'Test coverage', reason: 'Not measured.' },
    ],
    recommendations: [
      {
        id: 'high-quality',
        label: 'Address high-severity quality issues',
        description: '1 high-severity quality finding detected.',
        priority: 'high',
      },
    ],
  }

  const findings: PaginatedResponse<QualityFinding> = {
    items: [
      {
        id: 'finding-q1',
        title: 'Unused import detected',
        file: 'src/app.tsx',
        line: 3,
        severity: 'high',
        status: 'open',
        category: 'quality',
        rule: 'RUF001',
        repositoryId: 'repo-1',
        repositoryName: 'acme/web',
      },
    ],
    total: 1,
    page: 1,
    pageSize: 20,
    hasNext: false,
  }

  return { intelligenceFixture: intelligence, findingsFixture: findings }
})

vi.mock('@/api/findings', () => ({
  findingsApi: {
    qualityIntelligence: vi.fn().mockResolvedValue(intelligenceFixture),
    qualityFindings: vi.fn().mockResolvedValue(findingsFixture),
  },
}))

describe('CodeQualityPage', () => {
  it('renders quality posture, metrics, and findings', async () => {
    render(
      <MemoryRouter>
        <CodeQualityPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('ELEVATED DEBT')).toBeInTheDocument()
    expect(screen.getByText('Unused import detected')).toBeInTheDocument()
    expect(screen.getByText('Severity distribution')).toBeInTheDocument()
    expect(screen.getByText('Unavailable metrics')).toBeInTheDocument()
    expect(screen.getByText('Top issue patterns')).toBeInTheDocument()
    expect(screen.getByText('Recommended actions')).toBeInTheDocument()
  })
})
