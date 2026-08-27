import { MetricDefinition } from '@/components/dashboard/metric-definition'
import { EmptyState } from '@/components/states/empty-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatScore } from '@/lib/format-score'
import { cn } from '@/lib/utils'
import type { EngineeringHealth } from '@/types/api'

function dimensionTone(score: number | null | undefined): string {
  if (score == null) return 'bg-muted'
  if (score >= 80) return 'bg-success'
  if (score >= 60) return 'bg-warning'
  return 'bg-destructive'
}

export function EngineeringHealthPanel({ health }: { health: EngineeringHealth }) {
  const unavailable = health.score == null

  return (
    <Card className="h-full">
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Engineering health</CardTitle>
          <p className="mt-1 text-supporting">{health.definition}</p>
        </div>
        <MetricDefinition label="Engineering health" definition={health.definition} />
      </CardHeader>
      <CardContent className="space-y-5">
        {unavailable ? (
          <EmptyState
            title="No engineering health baseline"
            description="Complete repository analysis to calculate workspace health scores."
            className="min-h-32"
          />
        ) : (
          <>
            <div className="flex items-end gap-4">
              <p className="text-5xl font-semibold tabular-nums tracking-tight">{formatScore(health.score)}</p>
              <p className="pb-1 text-metadata capitalize">{health.level ?? 'unavailable'} risk profile</p>
            </div>

            <div className="space-y-3">
              <p className="text-section-heading">Contributing dimensions</p>
              <ul className="space-y-3">
                {health.dimensions.map((dimension) => (
                  <li key={dimension.key}>
                    <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                      <span className="font-medium">{dimension.label}</span>
                      <span className="font-mono tabular-nums text-muted-foreground">
                        {dimension.score != null ? formatScore(dimension.score) : '—'}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className={cn('h-full rounded-full transition-all', dimensionTone(dimension.score))}
                        style={{ width: `${Math.min(100, Math.max(0, dimension.score ?? 0))}%` }}
                        role="presentation"
                      />
                    </div>
                    <p className="mt-1 text-metadata">{dimension.definition}</p>
                  </li>
                ))}
              </ul>
            </div>

            {health.factors.length > 0 ? (
              <div>
                <p className="text-section-heading">Why this score?</p>
                <ul className="mt-2 space-y-1.5 text-supporting">
                  {health.factors.map((factor) => (
                    <li key={factor} className="flex gap-2">
                      <span aria-hidden="true">•</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  )
}
