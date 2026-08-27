import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnalysisSettingsPage } from '@/features/settings/analysis-settings-page'

vi.mock('@/api/organization', () => ({
  organizationApi: { analysisSettings: vi.fn() },
}))

import { organizationApi } from '@/api/organization'

describe('AnalysisSettingsPage', () => {
  beforeEach(() => {
    vi.mocked(organizationApi.analysisSettings).mockResolvedValue({
      automaticAnalysisOnConnect: true,
      webhookTriggeredAnalysis: true,
      analysisTimeoutSeconds: 3600,
      codeQualityScanners: [
        { name: 'Ruff', supported: true },
        { name: 'ESLint', supported: true },
      ],
      securityScanners: [{ name: 'Semgrep', supported: true }],
      dependencyScanners: [
        { name: 'pip-audit', supported: true },
        { name: 'npm', supported: false, reason: 'Not currently supported' },
      ],
    })
  })

  it('shows supported and unsupported scanners honestly', async () => {
    render(
      <MemoryRouter>
        <AnalysisSettingsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Ruff')).toBeInTheDocument()
    expect(screen.getByText(/not currently supported/i)).toBeInTheDocument()
  })
})
