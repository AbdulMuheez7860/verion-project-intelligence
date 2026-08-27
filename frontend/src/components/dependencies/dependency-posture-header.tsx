import { AlertTriangle, CheckCircle2, HelpCircle, Package } from 'lucide-react'
import type { DependencyFreshness, DependencyPosture } from '@/types/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/format-datetime'

function postureIcon(level: string) {
  switch (level) {
    case 'healthy':
      return CheckCircle2
    case 'medium':
      return HelpCircle
    case 'high':
    case 'critical':
      return AlertTriangle
    default:
      return Package
  }
}

function postureTone(level: string): 'healthy' | 'warning' | 'critical' | 'neutral' {
  switch (level) {
    case 'healthy':
      return 'healthy'
    case 'medium':
      return 'warning'
    case 'high':
      return 'warning'
    case 'critical':
      return 'critical'
    default:
      return 'neutral'
  }
}

interface DependencyPostureHeaderProps {
  posture: DependencyPosture
  healthScore?: number | null
  freshness: DependencyFreshness
  onRefresh?: () => void
  refreshing?: boolean
}

export function DependencyPostureHeader({
  posture,
  healthScore,
  freshness,
  onRefresh,
  refreshing = false,
}: DependencyPostureHeaderProps) {
  const Icon = postureIcon(posture.level)
  const tone = postureTone(posture.level)

  return (
    <Card className="overflow-hidden border-border">
      <CardContent className="p-0">
        <div
          className={cn(
            'flex flex-col gap-4 border-b border-border p-4 sm:flex-row sm:items-start sm:justify-between sm:p-5',
            tone === 'critical' && 'bg-severity-critical/5',
            tone === 'warning' && 'bg-severity-high/5',
            tone === 'healthy' && 'bg-severity-low/5',
          )}
        >
          <div className="flex min-w-0 items-start gap-3">
            <div
              className={cn(
                'flex size-10 shrink-0 items-center justify-center rounded-lg border',
                tone === 'critical' && 'border-severity-critical/30 bg-severity-critical/10 text-severity-critical',
                tone === 'warning' && 'border-severity-high/30 bg-severity-high/10 text-severity-high',
                tone === 'healthy' && 'border-severity-low/30 bg-severity-low/10 text-severity-low',
                tone === 'neutral' && 'border-border bg-muted text-muted-foreground',
              )}
              aria-hidden="true"
            >
              <Icon className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Dependency posture</p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold tracking-tight">{posture.label}</h2>
                {healthScore != null ? (
                  <Badge tone={postureTone(posture.level)}>Health {Math.round(healthScore)}</Badge>
                ) : (
                  <Badge tone="neutral">Unavailable</Badge>
                )}
              </div>
              <p className="mt-1.5 text-sm text-muted-foreground">{posture.explanation}</p>
            </div>
          </div>

          <div className="flex shrink-0 flex-col gap-2">
            <div
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm"
              role="status"
              aria-live="polite"
            >
              <p className="text-xs font-medium text-muted-foreground">Analysis status</p>
              <p className="mt-0.5 font-medium">{freshness.label}</p>
              {freshness.lastAnalyzedAt ? (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Last analyzed {formatRelativeTime(freshness.lastAnalyzedAt)}
                </p>
              ) : null}
              {freshness.isStale ? (
                <p className="mt-1 text-xs text-severity-high">Results may not reflect the latest code.</p>
              ) : null}
              {freshness.analysisRunning ? (
                <p className="mt-1 text-xs text-muted-foreground">Dependency analysis in progress.</p>
              ) : null}
            </div>
            {onRefresh ? (
              <Button type="button" variant="outline" size="sm" onClick={onRefresh} disabled={refreshing}>
                {refreshing ? 'Refreshing…' : 'Refresh'}
              </Button>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
