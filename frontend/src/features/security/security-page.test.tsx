import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { SecurityPage } from '@/features/security/security-page'
import type { PaginatedResponse, SecurityFinding, SecurityIntelligence } from '@/types/api'

const { intelligenceFixture, findingsFixture } = vi.hoisted(() => {
  const intelligence: SecurityIntelligence = {
    score: 65,
    severityCounts: { critical: 1, high: 1, medium: 1, low: 0 },
    hasAnalysisData: true,
    posture: {
      label: 'CRITICAL EXPOSURE',
      level: 'critical',
      explanation: '1 critical finding requires immediate review before release.',
    },
    freshness: {
      status: 'current',
      label: 'Analysis current',
      isStale: false,
      lastAnalyzedAt: new Date().toISOString(),
      analysisRunning: false,
    },
    totals: { open: 3, total: 3, repositoriesAffected: 1, connectedRepositories: 1 },
    categoryCounts: { security: 1, secret: 1, dependency: 1 },
    scannerCoverage: {
      executed: ['semgrep', 'bandit'],
      supported: ['semgrep', 'bandit'],
      hasData: true,
      note: 'Coverage reflects scanners executed in the latest completed analysis per repository.',
    },
    repositories: [{ id: 'repo-1', name: 'acme/api', findingCount: 3 }],
  }

  const findings: PaginatedResponse<SecurityFinding> = {
    items: [
      {
        id: 'finding-1',
        title: 'Unsafe auth middleware',
        file: 'app/auth.py',
        line: 12,
        severity: 'critical',
        status: 'open',
        category: 'security',
        repositoryId: 'repo-1',
        repositoryName: 'acme/api',
        ruleId: 'bandit.B101',
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
    securityIntelligence: vi.fn().mockResolvedValue(intelligenceFixture),
    securityFindings: vi.fn().mockResolvedValue(findingsFixture),
  },
}))

describe('SecurityPage', () => {
  it('renders security posture and findings from API', async () => {
    render(
      <MemoryRouter>
        <SecurityPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('CRITICAL EXPOSURE')).toBeInTheDocument()
    expect(await screen.findByText('Unsafe auth middleware')).toBeInTheDocument()
    expect(screen.getByText('Severity distribution')).toBeInTheDocument()
  })
})
