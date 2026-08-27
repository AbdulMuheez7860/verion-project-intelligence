import { Link } from 'react-router-dom'
import type { AnalyticsBaseline } from '@/types/api'
import { Card, CardContent } from '@/components/ui/card'

interface AnalyticsBaselineBannerProps {
  baseline: AnalyticsBaseline
}

export function AnalyticsBaselineBanner({ baseline }: AnalyticsBaselineBannerProps) {
  const title =
    baseline.status === 'building'
      ? 'Building your baseline'
      : baseline.status === 'established'
        ? 'Baseline established'
        : 'Historical trends available'

  return (
    <Card className="border-border">
      <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Baseline status</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">{title}</h2>
          <p className="mt-1.5 text-sm text-muted-foreground">{baseline.message}</p>
          {baseline.snapshotCount > 0 ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {baseline.snapshotCount} snapshot{baseline.snapshotCount !== 1 ? 's' : ''}
              {baseline.firstCapturedAt ? ` · since ${new Date(baseline.firstCapturedAt).toLocaleDateString()}` : ''}
            </p>
          ) : null}
        </div>
        {baseline.status === 'building' ? (
          <Link
            to="/app/repositories"
            className="inline-flex h-8 items-center rounded-md border border-border bg-background px-3 text-xs font-medium hover:bg-muted"
          >
            Analyze a repository
          </Link>
        ) : null}
      </CardContent>
    </Card>
  )
}
