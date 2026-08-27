import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AnalysisActivitySection } from '@/components/dashboard/analysis-activity-section'
import type { AnalysisActivityItem } from '@/types/api'

const activityFixture: AnalysisActivityItem[] = [
  {
    id: 'run-1',
    repositoryId: 'repo-1',
    repositoryName: 'acme/api',
    triggerSource: 'manual',
    startedAt: new Date('2026-03-01').toISOString(),
    durationSeconds: 95,
    status: 'complete',
    findingCount: 8,
    healthScore: 81,
    href: '/app/analysis-runs/run-1',
  },
]

describe('AnalysisActivitySection', () => {
  it('links activity items to analysis run detail', () => {
    render(
      <MemoryRouter>
        <AnalysisActivitySection activity={activityFixture} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Recent analysis activity')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: 'acme/api' })
    expect(link).toHaveAttribute('href', '/app/analysis-runs/run-1')
    expect(screen.getByText(/Findings 8/)).toBeInTheDocument()
    expect(screen.getByText(/Health 81/)).toBeInTheDocument()
  })
})
