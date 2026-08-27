import { Link } from 'react-router-dom'
import { LineChart } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { RecommendedAction, TrendsSection } from '@/types/api'

export function TrendsSectionPanel({ trends }: { trends: TrendsSection }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Engineering trends</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-start gap-3 rounded-lg border border-dashed border-border bg-muted/15 p-4">
          <LineChart className="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <div>
            <p className="text-sm font-medium">
              {trends.available ? 'Trend data available' : 'Building your baseline'}
            </p>
            <p className="mt-1 text-supporting">{trends.message}</p>
            {!trends.available && trends.completedAnalysesCount > 0 ? (
              <p className="mt-2 text-metadata">
                {trends.completedAnalysesCount} completed{' '}
                {trends.completedAnalysesCount === 1 ? 'analysis' : 'analyses'} recorded.
              </p>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function RecommendedActionsPanel({ actions }: { actions: RecommendedAction[] }) {
  if (actions.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommended next actions</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {actions.map((action) => (
            <li key={action.id} className="rounded-lg border border-border p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-medium">{action.label}</p>
                  <p className="mt-1 text-supporting">{action.description}</p>
                </div>
                <Link to={action.href} className="shrink-0 text-sm font-medium text-primary hover:underline">
                  Go
                </Link>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
