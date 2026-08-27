import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { GlobalAnalysisRunDetailPage } from '@/features/analysis-runs/analysis-run-detail-page'
import type { AnalysisRunDetail } from '@/types/api'

const detailFixture: AnalysisRunDetail = {
  id: 'run-1',
  repositoryId: 'repo-1',
  repositoryName: 'acme/api',
  status: 'failed',
  trigger: 'manual',
  findingCount: 0,
  capabilities: { canRetry: true, canCancel: false },
  repositoryHref: '/app/repositories/repo-1',
  error: 'GitHub integration not connected.',
  analyzerSummary: {
    executed: ['ruff'],
    skipped: [{ name: 'semgrep', reason: 'Unsupported for this repository' }],
    failed: [],
    dependencyScan: false,
    repositoryMetricsStatus: 'failed',
  },
}

vi.mock('@/hooks/use-analysis-run', () => ({
  useAnalysisRun: vi.fn(),
}))

vi.mock('@/hooks/use-permissions', () => ({
  usePermissions: () => ({ canRetry: true, canCancel: true, canAnalyze: true, isViewer: false, role: 'member' }),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ push: vi.fn(), dismiss: vi.fn(), toasts: [] }),
}))

import { useAnalysisRun } from '@/hooks/use-analysis-run'

describe('GlobalAnalysisRunDetailPage', () => {
  beforeEach(() => {
    vi.mocked(useAnalysisRun).mockReturnValue({
      status: 'success',
      data: detailFixture,
      error: null,
      refetch: vi.fn(),
    })
  })

  it('renders failed run with error and retry action', async () => {
    render(
      <MemoryRouter initialEntries={['/app/analysis-runs/run-1']}>
        <Routes>
          <Route path="/app/analysis-runs/:analysisId" element={<GlobalAnalysisRunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByText('Run execution')).toBeInTheDocument()
    expect(screen.getByText('GitHub integration not connected.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(screen.getByText(/semgrep/)).toBeInTheDocument()
  })

  it('shows active polling message for running runs', async () => {
    vi.mocked(useAnalysisRun).mockReturnValue({
      status: 'success',
      data: { ...detailFixture, status: 'running', capabilities: { canRetry: false, canCancel: false } },
      error: null,
      refetch: vi.fn(),
    })
    render(
      <MemoryRouter initialEntries={['/app/analysis-runs/run-1']}>
        <Routes>
          <Route path="/app/analysis-runs/:analysisId" element={<GlobalAnalysisRunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByText(/refreshes automatically every 5 seconds/i)).toBeInTheDocument()
  })
})
