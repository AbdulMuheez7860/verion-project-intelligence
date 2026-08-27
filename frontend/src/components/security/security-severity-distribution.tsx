import type { SeverityCounts } from '@/types/api'
import { EmptyState } from '@/components/states/empty-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const bucketConfig = [
  { key: 'critical', label: 'Critical', className: 'text-severity-critical', bar: 'bg-severity-critical' },
  { key: 'high', label: 'High', className: 'text-severity-high', bar: 'bg-severity-high' },
  { key: 'medium', label: 'Medium', className: 'text-severity-medium', bar: 'bg-severity-medium' },
  { key: 'low', label: 'Low', className: 'text-severity-low', bar: 'bg-severity-low' },
] as const

interface SecuritySeverityDistributionProps {
  counts?: SeverityCounts | null
  hasData: boolean
  total?: number
}

export function SecuritySeverityDistribution({ counts, hasData, total }: SecuritySeverityDistributionProps) {
  const computedTotal =
    total ??
    (counts ? counts.critical + counts.high + counts.medium + counts.low : 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Severity distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData || !counts ? (
          <EmptyState
            title="No severity data"
            description="Severity distribution appears after security analysis completes."
            className="min-h-28"
          />
        ) : (
          <div>
            <p className="sr-only">
              Security findings distribution:{' '}
              {bucketConfig.map((bucket) => `${bucket.label} ${counts[bucket.key]}`).join(', ')}
            </p>
            <ul className="space-y-3" aria-hidden="true">
              {bucketConfig.map((bucket) => {
                const count = counts[bucket.key]
                const width = computedTotal > 0 ? (count / computedTotal) * 100 : 0
                return (
                  <li key={bucket.key}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className={`font-medium ${bucket.className}`}>{bucket.label}</span>
                      <span className="font-mono tabular-nums text-muted-foreground">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${bucket.bar}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
            <p className="mt-4 text-metadata">{computedTotal} total security findings</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
