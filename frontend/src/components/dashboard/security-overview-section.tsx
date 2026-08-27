import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/states/empty-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { SecurityOverview } from '@/types/api'

export function SecurityOverviewSection({ security }: { security: SecurityOverview }) {
  const counts = security.severityCounts

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Security overview</CardTitle>
        <Link to="/app/security" className="text-sm font-medium text-primary hover:underline">
          View all findings
        </Link>
      </CardHeader>
      <CardContent>
        {!security.hasData || !counts ? (
          <EmptyState
            title="No security findings"
            description="Security severity counts appear after analysis completes."
            className="min-h-32"
          />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'Critical', value: counts.critical, className: 'text-severity-critical' },
              { label: 'High', value: counts.high, className: 'text-severity-high' },
              { label: 'Medium', value: counts.medium, className: 'text-severity-medium' },
              { label: 'Low', value: counts.low, className: 'text-severity-low' },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border border-border px-3 py-3">
                <p className="text-metric-label">{item.label}</p>
                <p className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${item.className}`}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
