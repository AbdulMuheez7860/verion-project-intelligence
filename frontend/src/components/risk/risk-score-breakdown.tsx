import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { RiskLevel, RiskScore } from '@/types/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

function riskTone(level: RiskLevel | string | undefined): 'healthy' | 'warning' | 'critical' | 'neutral' {
  switch (level) {
    case 'critical':
    case 'high':
      return 'critical'
    case 'medium':
      return 'warning'
    default:
      return 'healthy'
  }
}

function riskLabel(level: RiskLevel | string | undefined): string {
  if (!level) return 'Unknown'
  return level.charAt(0).toUpperCase() + level.slice(1)
}

export function RiskScoreBreakdown({ risk }: { risk: RiskScore }) {
  const [expanded, setExpanded] = useState(risk.value >= 50)

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0 border-b-0 pb-0">
        <div>
          <p className="text-label">{risk.engine ?? 'Verion Risk Engine'}</p>
          <CardTitle className="mt-1">PR risk score</CardTitle>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={riskTone(risk.level)}>
            <span className="font-mono tabular-nums">{risk.value}</span>
            <span className="text-muted-foreground">·</span>
            {riskLabel(risk.level)}
          </Badge>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setExpanded((open) => !open)}
            aria-expanded={expanded}
          >
            Why is this {risk.value >= 50 ? 'high' : ''} risk?
            <ChevronDown
              className={cn('size-3.5 transition-transform', expanded && 'rotate-180')}
              aria-hidden="true"
            />
          </Button>
        </div>
      </CardHeader>

      {expanded ? (
        <CardContent className="pt-0">
          <div className="rounded-md border border-border bg-muted/20 p-4">
            <p className="text-label mb-3">Factor breakdown</p>
            <ul className="space-y-2.5">
              {risk.factors.map((factor) => (
                <li key={factor.label} className="grid grid-cols-[1fr_auto] gap-3 text-sm">
                  <div>
                    <p className="font-medium">{factor.label}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{factor.explanation}</p>
                  </div>
                  <span className="font-mono text-xs tabular-nums text-muted-foreground">
                    +{factor.contribution}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-sm font-medium">
              <span>Total</span>
              <span className="font-mono tabular-nums">
                {risk.value}
                <span className="ml-2 text-xs font-normal uppercase tracking-wide text-muted-foreground">
                  {riskLabel(risk.level)}
                </span>
              </span>
            </div>
          </div>
        </CardContent>
      ) : null}
    </Card>
  )
}
