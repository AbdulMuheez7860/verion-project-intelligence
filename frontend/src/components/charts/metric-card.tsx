import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export function MetricCard({
  label,
  value,
  detail,
  unavailableReason,
  action,
  isLoading = false,
  className,
}: {
  label: string
  value?: ReactNode
  detail?: string
  unavailableReason?: string
  action?: ReactNode
  isLoading?: boolean
  className?: string
}) {
  const unavailable = value === undefined || value === null

  return (
    <Card className={cn(className)}>
      <CardContent className="p-0">
        <div className="px-4 py-3">
          <p className="text-label">{label}</p>
          {isLoading ? (
            <Skeleton className="mt-2 h-7 w-20" />
          ) : unavailable ? (
            <div className="mt-2">
              <p className="font-mono text-lg font-semibold tabular-nums text-muted-foreground">—</p>
              <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
                {unavailableReason ?? 'No analysis data is available yet.'}
              </p>
              {action ? <div className="mt-2.5">{action}</div> : null}
            </div>
          ) : (
            <div className="mt-2">
              <p className="font-mono text-xl font-semibold tabular-nums tracking-tight">{value}</p>
              {detail ? <p className="mt-1 text-xs text-muted-foreground">{detail}</p> : null}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function AnalyzeRepositoryButton({
  onClick,
  disabled,
}: {
  onClick?: () => void
  disabled?: boolean
}) {
  return (
    <Button size="sm" variant="outline" onClick={onClick} disabled={disabled}>
      Analyze repository
    </Button>
  )
}
