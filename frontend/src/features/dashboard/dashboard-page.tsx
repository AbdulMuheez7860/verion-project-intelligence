import { Link } from 'react-router-dom'
import { DashboardHeader } from '@/components/dashboard/dashboard-header'
import { OverviewMetrics } from '@/components/dashboard/overview-metrics'
import { EngineeringHealthPanel } from '@/components/dashboard/engineering-health-panel'
import { AttentionSection } from '@/components/dashboard/attention-section'
import { RepositoryHealthSection } from '@/components/dashboard/repository-health-section'
import { RiskDistributionPanel } from '@/components/dashboard/risk-distribution-panel'
import { PullRequestIntelligenceSection } from '@/components/dashboard/pull-request-intelligence-section'
import { SecurityOverviewSection } from '@/components/dashboard/security-overview-section'
import { AnalysisActivitySection } from '@/components/dashboard/analysis-activity-section'
import { RecommendedActionsPanel, TrendsSectionPanel } from '@/components/dashboard/trends-and-actions'
import { ErrorState } from '@/components/states/error-state'
import { PageSkeleton } from '@/components/states/skeletons'
import { EmptyState } from '@/components/states/empty-state'
import { Button } from '@/components/ui/button'
import { useDashboardSummary } from '@/hooks/use-dashboard'

export function DashboardPage() {
  const { data, status, error, requestId, isUnavailable, lastUpdated, isRefreshing, refetch } =
    useDashboardSummary()

  if (status === 'loading') {
    return (
      <div className="space-y-6">
        <DashboardHeader
          lastUpdated={null}
          isRefreshing={false}
          hasActiveAnalysis={false}
          onRefresh={() => void refetch()}
        />
        <PageSkeleton />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="space-y-6">
        <DashboardHeader
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          hasActiveAnalysis={false}
          onRefresh={() => void refetch()}
        />
        <ErrorState
          title="Dashboard unavailable"
          description={error ?? 'Unable to load dashboard data.'}
          requestId={requestId ?? undefined}
          onRetry={() => void refetch()}
        />
      </div>
    )
  }

  if (isUnavailable || !data) {
    return (
      <div className="space-y-6">
        <DashboardHeader
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          hasActiveAnalysis={false}
          onRefresh={() => void refetch()}
        />
        <EmptyState
          title="Backend not connected"
          description="Start the FastAPI backend to load live engineering intelligence."
          action={
            <Button asChild variant="secondary" size="sm">
              <Link to="/app/settings/integrations">Configure integrations</Link>
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <DashboardHeader
        lastUpdated={lastUpdated}
        isRefreshing={isRefreshing}
        hasActiveAnalysis={data.hasActiveAnalysis}
        onRefresh={() => void refetch()}
      />

      <OverviewMetrics metrics={data.overview} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <EngineeringHealthPanel health={data.health} />
        <AttentionSection items={data.attention} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <RiskDistributionPanel distribution={data.riskDistribution} />
        <SecurityOverviewSection security={data.security} />
      </div>

      <RepositoryHealthSection repositories={data.repositories} />

      <PullRequestIntelligenceSection pullRequests={data.pullRequests} />

      <AnalysisActivitySection activity={data.analysisActivity} />

      <div className="grid gap-6 xl:grid-cols-2">
        <TrendsSectionPanel trends={data.trends} />
        <RecommendedActionsPanel actions={data.recommendedActions} />
      </div>
    </div>
  )
}
