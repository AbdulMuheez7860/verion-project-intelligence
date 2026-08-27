import { AlertTriangle, CheckCircle2, HelpCircle, ShieldAlert } from 'lucide-react'
import type { MergeSafetyVerdict as MergeSafetyVerdictType, PRFreshness } from '@/types/api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/format-datetime'
import { riskLevelTone } from '@/lib/risk-tone'

function verdictIcon(key: string) {
  switch (key) {
    case 'safe_to_merge':
      return CheckCircle2
    case 'review_recommended':
      return HelpCircle
    case 'high_risk':
    case 'critical_risk':
      return ShieldAlert
    default:
      return AlertTriangle
  }
}

function verdictTone(key: string): 'healthy' | 'warning' | 'critical' | 'neutral' {
  switch (key) {
    case 'safe_to_merge':
      return 'healthy'
    case 'review_recommended':
      return 'warning'
    case 'high_risk':
      return 'warning'
    case 'critical_risk':
      return 'critical'
    default:
      return 'neutral'
  }
}

export function MergeSafetyHeader({
  verdict,
  freshness,
}: {
  verdict: MergeSafetyVerdictType
  freshness: PRFreshness
}) {
  const Icon = verdictIcon(verdict.key)
  const tone = verdictTone(verdict.key)
  const freshnessLabel =
    freshness.status === 'current' && freshness.riskScoredAt
      ? `Analyzed ${formatRelativeTime(freshness.riskScoredAt)}`
      : freshness.label

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div
          className={cn(
            'border-b border-border px-5 py-4',
            tone === 'critical' && 'bg-destructive/5',
            tone === 'warning' && 'bg-warning/8',
            tone === 'healthy' && 'bg-success/5',
            tone === 'neutral' && 'bg-muted/20',
          )}
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  'grid size-11 shrink-0 place-items-center rounded-lg border',
                  tone === 'critical' && 'border-destructive/30 bg-destructive/10 text-destructive',
                  tone === 'warning' && 'border-warning/35 bg-warning/12 text-warning-foreground',
                  tone === 'healthy' && 'border-success/30 bg-success/10 text-success',
                  tone === 'neutral' && 'border-border bg-muted text-muted-foreground',
                )}
                aria-hidden="true"
              >
                <Icon className="size-5" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Merge safety</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight">{verdict.label}</h2>
                <p className="mt-1 text-sm font-medium">{verdict.headline}</p>
                {verdict.explanation ? (
                  <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{verdict.explanation}</p>
                ) : null}
              </div>
            </div>
            <div className="flex flex-col items-start gap-2 sm:items-end">
              {verdict.riskScore != null ? (
                <Badge tone={riskLevelTone(verdict.riskLevel)}>
                  <span className="font-mono tabular-nums">Score {verdict.riskScore}</span>
                </Badge>
              ) : (
                <Badge tone="neutral">Score unavailable</Badge>
              )}
              <p className="text-xs text-muted-foreground" aria-live="polite">
                {freshnessLabel}
              </p>
            </div>
          </div>
          {freshness.isStale && freshness.detail ? (
            <p className="mt-3 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning-foreground" role="alert">
              {freshness.detail}
            </p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
