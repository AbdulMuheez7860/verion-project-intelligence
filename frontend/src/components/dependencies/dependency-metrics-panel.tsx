import type { DependencyScannerCoverage, DependencyTotals, SeverityCounts } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface DependencyMetricsPanelProps {
  totals: DependencyTotals
  severityCounts?: SeverityCounts | null
  scannerCoverage: DependencyScannerCoverage
  hasData: boolean
}

export function DependencyMetricsPanel({
  totals,
  severityCounts,
  scannerCoverage,
  hasData,
}: DependencyMetricsPanelProps) {
  const ecosystemsScanned = scannerCoverage.ecosystems.filter((eco) => eco.supported).length

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Dependencies analyzed</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-2xl font-semibold tabular-nums">{hasData ? totals.total : '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {hasData ? `${totals.connectedRepositories} connected repositories` : 'Not analyzed'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Vulnerable dependencies</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-2xl font-semibold tabular-nums">{hasData ? totals.vulnerable : '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">From pip-audit vulnerability findings</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Critical / high</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-2xl font-semibold tabular-nums">
            {hasData && severityCounts
              ? `${severityCounts.critical} / ${severityCounts.high}`
              : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Severity from dependency vulnerability findings</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Affected repositories</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-2xl font-semibold tabular-nums">
            {hasData ? totals.repositoriesAffected : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Repositories with vulnerable dependencies</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Ecosystems scanned</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-2xl font-semibold tabular-nums">
            {hasData ? ecosystemsScanned : '—'}
          </p>
          {scannerCoverage.hasData ? (
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
              {scannerCoverage.executed.map((scanner) => (
                <li key={scanner} className="font-mono">
                  {scanner}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">Not available</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
