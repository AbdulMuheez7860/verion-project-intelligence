import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/page-header'
import { PAGE_PURPOSE } from '@/lib/page-purpose'

export function DashboardHeader({
  lastUpdated,
  isRefreshing,
  hasActiveAnalysis,
  onRefresh,
}: {
  lastUpdated: Date | null
  isRefreshing: boolean
  hasActiveAnalysis: boolean
  onRefresh: () => void
}) {
  return (
    <PageHeader
      title="Dashboard"
      purpose={PAGE_PURPOSE.dashboard}
      description="Engineering intelligence for your workspace — health, risk, and what needs attention now."
      action={
        <div className="flex flex-col items-end gap-2">
          {lastUpdated ? (
            <p className="text-metadata">
              Last updated {lastUpdated.toLocaleTimeString()}
              {hasActiveAnalysis ? ' · Analysis in progress' : ''}
            </p>
          ) : null}
          <Button variant="secondary" size="sm" onClick={onRefresh} loading={isRefreshing} aria-label="Refresh dashboard">
            <RefreshCw className="size-4" />
            Refresh
          </Button>
        </div>
      }
    />
  )
}
