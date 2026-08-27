import type { ScannerCoverage, SecurityCategoryCounts, SecurityTotals } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { METRIC_DEFINITIONS } from '@/lib/metric-definitions'

interface SecurityMetricsPanelProps {
  totals: SecurityTotals
  categoryCounts: SecurityCategoryCounts
  scannerCoverage: ScannerCoverage
  score?: number | null
  hasData: boolean
}

export function SecurityMetricsPanel({
  totals,
  categoryCounts,
  scannerCoverage,
  score,
  hasData,
}: SecurityMetricsPanelProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Security score</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-semibold tabular-nums">
            {hasData && score != null ? Math.round(score) : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{METRIC_DEFINITIONS.security}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Open findings</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-3xl font-semibold tabular-nums">
            {hasData ? totals.open : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {hasData ? `${totals.total} total across ${totals.repositoriesAffected} repositories` : 'Not analyzed'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Finding categories</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {hasData ? (
            <>
              <p>
                <span className="text-muted-foreground">Code security:</span>{' '}
                <span className="font-mono tabular-nums">{categoryCounts.security}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Secrets:</span>{' '}
                <span className="font-mono tabular-nums">{categoryCounts.secret}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Dependencies:</span>{' '}
                <span className="font-mono tabular-nums">{categoryCounts.dependency}</span>
              </p>
            </>
          ) : (
            <p className="text-muted-foreground">Not available until analysis completes.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Scanner coverage</CardTitle>
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
