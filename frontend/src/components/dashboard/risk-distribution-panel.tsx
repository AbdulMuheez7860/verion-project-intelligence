import { EmptyState } from '@/components/states/empty-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { RiskDistribution } from '@/types/api'

const bucketColors: Record<string, string> = {
  critical: 'bg-severity-critical',
  high: 'bg-severity-high',
  medium: 'bg-severity-medium',
  low: 'bg-severity-low',
}

export function RiskDistributionPanel({ distribution }: { distribution: RiskDistribution }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Security risk distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {!distribution.hasData ? (
          <EmptyState
            title="No security findings"
            description="Severity distribution appears after security analysis completes."
            className="min-h-32"
          />
        ) : (
          <div>
            <p className="sr-only">
              Security findings distribution:{' '}
              {distribution.buckets.map((bucket) => `${bucket.label} ${bucket.count}`).join(', ')}
            </p>
            <ul className="space-y-3" aria-hidden="true">
              {distribution.buckets.map((bucket) => {
                const width = distribution.total > 0 ? (bucket.count / distribution.total) * 100 : 0
                return (
                  <li key={bucket.key}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium">{bucket.label}</span>
                      <span className="font-mono tabular-nums text-muted-foreground">{bucket.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${bucketColors[bucket.key] ?? 'bg-muted-foreground'}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
            <p className="mt-4 text-metadata">{distribution.total} total open security findings</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
