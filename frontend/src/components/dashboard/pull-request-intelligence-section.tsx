import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/states/empty-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { riskScoreTone } from '@/lib/risk-tone'
import type { PullRequestDashboardItem, PullRequestSection } from '@/types/api'

function verdictTone(verdict: PullRequestDashboardItem['verdict']) {
  if (verdict === 'critical_risk' || verdict === 'high_risk') return 'critical' as const
  if (verdict === 'review_recommended') return 'warning' as const
  if (verdict === 'safe_to_merge') return 'healthy' as const
  return 'neutral' as const
}

function PrList({ title, items, emptyTitle, emptyDescription }: {
  title: string
  items: PullRequestDashboardItem[]
  emptyTitle: string
  emptyDescription: string
}) {
  return (
    <div>
      <h3 className="text-section-heading">{title}</h3>
      {items.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} className="mt-3 min-h-28" />
      ) : (
        <ul className="mt-3 divide-y divide-border">
          {items.map((pr) => (
            <li key={pr.id} className="flex flex-col gap-2 py-3 first:pt-0 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="text-metadata">{pr.repositoryName}</p>
                <Link to={`/app/pull-requests/${pr.id}`} className="font-medium hover:underline">
                  #{pr.id} {pr.title}
                </Link>
                {pr.verdictReason ? <p className="mt-1 text-supporting">{pr.verdictReason}</p> : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={verdictTone(pr.verdict)}>{pr.verdictLabel}</Badge>
                {pr.riskScore != null ? (
                  <Badge tone={riskScoreTone(pr.riskScore)}>
                    <span className="font-mono tabular-nums">{pr.riskScore}</span>
                  </Badge>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function PullRequestIntelligenceSection({ pullRequests }: { pullRequests: PullRequestSection }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Pull request intelligence</CardTitle>
        <Link to="/app/pull-requests" className="text-sm font-medium text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent className="space-y-6">
        <PrList
          title="High-risk pull requests"
          items={pullRequests.highRisk}
          emptyTitle="No high-risk pull requests"
          emptyDescription="Open pull requests with elevated risk scores will appear here."
        />
        <PrList
          title="Awaiting analysis"
          items={pullRequests.awaitingAnalysis}
          emptyTitle="No PRs awaiting analysis"
          emptyDescription="Pull requests without risk scores appear here until analysis completes."
        />
      </CardContent>
    </Card>
  )
}
