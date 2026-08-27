import { useEffect, useState } from 'react'
import { organizationApi } from '@/api/organization'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisSettings } from '@/types/api'

export function AnalysisSettingsPage() {
  const [data, setData] = useState<AnalysisSettings | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    organizationApi
      .analysisSettings()
      .then((settings) => {
        setData(settings)
        setStatus('success')
      })
      .catch(() => setStatus('error'))
  }, [])

  if (status === 'loading') return <LoadingState label="Loading analysis settings…" />
  if (status === 'error' || !data) return <ErrorState title="Unable to load analysis settings" />

  const renderScanners = (title: string, scanners: AnalysisSettings['codeQualityScanners']) => (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-2 space-y-1 text-sm">
        {scanners.map((scanner) => (
          <li key={scanner.name} className="flex items-start gap-2">
            <span aria-hidden="true">{scanner.supported ? '✓' : '○'}</span>
            <span>
              {scanner.name}
              {!scanner.supported && scanner.reason ? (
                <span className="text-muted-foreground"> — {scanner.reason}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 text-sm">
        <dl className="grid gap-2 sm:grid-cols-2">
          <div><dt className="text-muted-foreground">Automatic analysis on connect</dt><dd>{data.automaticAnalysisOnConnect ? 'Enabled' : 'Disabled'}</dd></div>
          <div><dt className="text-muted-foreground">Webhook-triggered analysis</dt><dd>{data.webhookTriggeredAnalysis ? 'Enabled' : 'Disabled'}</dd></div>
          <div><dt className="text-muted-foreground">Analysis timeout</dt><dd>{Math.round(data.analysisTimeoutSeconds / 60)} minutes</dd></div>
        </dl>
        {renderScanners('Code quality', data.codeQualityScanners)}
        {renderScanners('Security', data.securityScanners)}
        {renderScanners('Dependencies', data.dependencyScanners)}
        <p className="text-xs text-muted-foreground">Scanner configuration is determined by the analysis pipeline. Unsupported ecosystems are shown as unavailable.</p>
      </CardContent>
    </Card>
  )
}
