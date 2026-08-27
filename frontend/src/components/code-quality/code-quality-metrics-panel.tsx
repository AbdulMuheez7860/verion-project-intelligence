import type { QualityScannerCoverage, QualityTotals } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { METRIC_DEFINITIONS } from '@/lib/metric-definitions'

interface CodeQualityMetricsPanelProps {
  totals: QualityTotals
  scannerCoverage: QualityScannerCoverage
  score?: number | null
  hasData: boolean
}

export function CodeQualityMetricsPanel({
  totals,
  scannerCoverage,
  score,
  hasData,
}: CodeQualityMetricsPanelProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Quality score</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-semibold tabular-nums">
            {hasData && score != null ? Math.round(score) : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{METRIC_DEFINITIONS.code_quality}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Open findings</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-semibold tabular-nums">{hasData ? totals.open : '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {hasData ? `${totals.total} total across ${totals.repositoriesAffected} repositories` : 'Not analyzed'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Critical / high</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-semibold tabular-nums">
            {hasData ? `${totals.critical} / ${totals.high}` : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Highest-priority quality issues</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Affected repositories</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-semibold tabular-nums">
            {hasData ? totals.repositoriesAffected : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {hasData ? `${totals.connectedRepositories} connected` : 'Not analyzed'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Analyzer coverage</CardTitle>
        </CardHeader>
        <CardContent>
          {scannerCoverage.hasData ? (
            <ul className="space-y-1 text-sm">
              {scannerCoverage.executed.map((scanner) => (
                <li key={scanner} className="font-mono text-xs">
                  {scanner}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Not available</p>
          )}
          {scannerCoverage.note ? (
            <p className="mt-2 text-xs text-muted-foreground">{scannerCoverage.note}</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
