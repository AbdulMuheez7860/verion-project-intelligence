import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/states/empty-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateTime, formatDuration } from '@/lib/format-datetime'
import type { AnalysisActivityItem } from '@/types/api'

function statusTone(status: string) {
  if (status === 'failed') return 'critical' as const
  if (status === 'running' || status === 'queued') return 'warning' as const
  if (status === 'complete') return 'healthy' as const
  return 'neutral' as const
}

export function AnalysisActivitySection({ activity }: { activity: AnalysisActivityItem[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Recent analysis activity</CardTitle>
        <Link to="/app/analysis-runs" className="text-xs font-medium text-primary hover:underline">
          View all runs
        </Link>
      </CardHeader>
      <CardContent>
        {activity.length === 0 ? (
          <EmptyState
            title="No analysis history"
            description="Repository analysis runs will appear here with status and duration."
            className="min-h-32"
          />
        ) : (
          <ul className="divide-y divide-border">
            {activity.map((run) => (
              <li key={run.id} className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <Link to={run.href} className="font-medium hover:underline">
                    {run.repositoryName}
                  </Link>
                  <p className="mt-1 text-supporting">
                    {run.triggerSource}
                    {run.commitSha ? ` · ${run.commitSha.slice(0, 7)}` : ''}
                    {run.startedAt ? ` · ${formatDateTime(run.startedAt)}` : ''}
                  </p>
                  {run.error ? <p className="mt-1 text-xs text-destructive">{run.error}</p> : null}
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge tone={statusTone(run.status)}>{run.status}</Badge>
                  <span className="text-metadata">Duration {formatDuration(run.durationSeconds)}</span>
                  <span className="font-mono tabular-nums text-metadata">
                    Findings {run.findingCount}
                  </span>
                  <span className="font-mono tabular-nums text-metadata">
                    Health {run.healthScore != null ? Math.round(run.healthScore) : '—'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
