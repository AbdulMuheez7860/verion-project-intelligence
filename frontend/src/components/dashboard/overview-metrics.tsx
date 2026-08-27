import { Link } from 'react-router-dom'
import { MetricDefinition } from '@/components/dashboard/metric-definition'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { OverviewMetric, OverviewStatus } from '@/types/api'
import { formatScore } from '@/lib/format-score'

const statusStyles: Record<OverviewStatus, string> = {
  healthy: 'border-success/30 bg-success/5',
  warning: 'border-warning/35 bg-warning/8',
  critical: 'border-destructive/30 bg-destructive/5',
  neutral: 'border-border bg-card',
  unavailable: 'border-border bg-muted/20',
}

function formatValue(metric: OverviewMetric): string {
  if (metric.value === null || metric.value === undefined) return '—'
  if (metric.key === 'engineering_health') {
    return formatScore(Number(metric.value)) ?? '—'
  }
  return String(metric.value)
}

export function OverviewMetrics({ metrics }: { metrics: OverviewMetric[] }) {
  return (
    <section aria-label="Workspace overview">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
        {metrics.map((metric) => {
          const content = (
            <Card className={cn('h-full transition-colors hover:border-primary/30', statusStyles[metric.status])}>
              <CardContent className="flex h-full flex-col gap-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-metric-label">{metric.label}</p>
                  <MetricDefinition label={metric.label} definition={metric.definition} />
                </div>
                <p className="text-metric">{formatValue(metric)}</p>
                {metric.value === null || metric.value === undefined ? (
                  <p className="text-metadata">No analysis yet</p>
                ) : null}
              </CardContent>
            </Card>
          )

          return metric.href ? (
            <Link key={metric.key} to={metric.href} className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              {content}
            </Link>
          ) : (
            <div key={metric.key}>{content}</div>
          )
        })}
      </div>
    </section>
  )
}
