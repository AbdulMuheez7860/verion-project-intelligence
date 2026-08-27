import { Link } from 'react-router-dom'
import type { AnalysisRunSnapshotSummary } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface SnapshotLinkagePanelProps {
  snapshot: AnalysisRunSnapshotSummary | null | undefined
  analyticsHref?: string | null
}

function score(value: number | null | undefined): string {
  return value == null ? '—' : String(Math.round(value))
}

export function SnapshotLinkagePanel({ snapshot, analyticsHref }: SnapshotLinkagePanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Historical snapshot</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          Immutable snapshot data captured when this analysis completed successfully. Execution metadata above
          reflects the run; scores below are frozen at capture time.
        </p>
        {snapshot ? (
          <>
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-muted-foreground">Health</dt>
                <dd className="font-mono tabular-nums">{score(snapshot.healthScore)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Security</dt>
                <dd className="font-mono tabular-nums">{score(snapshot.securityScore)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Quality</dt>
                <dd className="font-mono tabular-nums">{score(snapshot.qualityScore)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Dependencies</dt>
                <dd className="font-mono tabular-nums">{score(snapshot.dependencyScore)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">PR risk</dt>
                <dd className="font-mono tabular-nums">{score(snapshot.prRiskScore)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Captured</dt>
                <dd>{snapshot.capturedAt ? new Date(snapshot.capturedAt).toLocaleString() : '—'}</dd>
              </div>
            </dl>
            {analyticsHref ? (
              <Link to={analyticsHref} className="text-sm font-medium text-primary hover:underline">
                View historical analytics →
              </Link>
            ) : null}
          </>
        ) : (
          <p className="text-muted-foreground">
            No snapshot — only successful analyses create historical snapshots.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
