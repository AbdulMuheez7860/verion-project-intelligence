import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { analyticsApi } from '@/api/analytics'
import { AnalyticsBaselineBanner } from '@/components/analytics/analytics-baseline-banner'
import { AnalyticsChangesPanel } from '@/components/analytics/analytics-changes-panel'
import { AnalyticsRepositoryComparisonTable } from '@/components/analytics/analytics-repository-comparison'
import { AnalyticsTrendChart } from '@/components/analytics/analytics-trend-chart'
import { PageHeader } from '@/components/layout/page-header'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PAGE_PURPOSE } from '@/lib/page-purpose'
import type { AnalyticsOverview } from '@/types/api'

function buildTrendSummary(
  label: string,
  points: { capturedAt: string; value?: number | null }[],
): string | undefined {
  const values = points.map((p) => p.value).filter((v): v is number => v != null)
  if (values.length < 2) return undefined
  const first = values[0]
  const last = values[values.length - 1]
  const direction = last > first ? 'increased' : last < first ? 'decreased' : 'remained stable'
  return `${label} ${direction} from ${Math.round(first)} to ${Math.round(last)} across ${values.length} snapshots.`
}

export function AnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const repositoryId = searchParams.get('repositoryId') ?? undefined
  const range = searchParams.get('range') ?? '90d'

  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [error, setError] = useState<string | null>(null)

  const params = useMemo(() => {
    const days = Number.parseInt(range.replace('d', ''), 10) || 90
    const to = new Date()
    const from = new Date(to.getTime() - days * 24 * 60 * 60 * 1000)
    return {
      repositoryId,
      from: from.toISOString(),
      to: to.toISOString(),
    }
  }, [repositoryId, range])

  const loadOverview = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const result = await analyticsApi.overview(params)
      setOverview(result)
      setStatus('success')
    } catch (err) {
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Failed to load analytics.')
    }
  }, [params])

  useEffect(() => {
    void loadOverview()
  }, [loadOverview])

  const updateParams = useCallback(
    (updates: Record<string, string | undefined>) => {
      const next = new URLSearchParams(searchParams)
      for (const [key, value] of Object.entries(updates)) {
        if (!value) next.delete(key)
        else next.set(key, value)
      }
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )

  const canShowTrends = (overview?.baseline.snapshotCount ?? 0) >= 2
  const isInitialLoading = status === 'loading' && !overview

  return (
    <div className="space-y-5">
      <PageHeader
        title="Analytics"
        purpose={PAGE_PURPOSE.analytics}
        description={
          overview?.baseline.available
            ? `${overview.baseline.snapshotCount} historical snapshot(s) · ${overview.rangeDays}-day window`
            : undefined
        }
      />

      {isInitialLoading ? <LoadingState label="Loading historical analytics…" /> : null}
      {status === 'error' ? <ErrorState description={error ?? undefined} onRetry={() => void loadOverview()} /> : null}

      {status === 'success' && overview ? (
        <>
          <AnalyticsBaselineBanner baseline={overview.baseline} />

          <Card>
            <CardHeader className="space-y-3">
              <CardTitle>Filters</CardTitle>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <label className="grid gap-1.5 text-sm">
                  <span className="font-medium">Repository</span>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3"
                    value={repositoryId ?? ''}
                    onChange={(e) => updateParams({ repositoryId: e.target.value || undefined })}
                    aria-label="Filter by repository"
                  >
                    <option value="">All repositories</option>
                    {overview.repositoryOptions.map((repo) => (
                      <option key={repo.id} value={repo.id}>
                        {repo.name} ({repo.snapshotCount})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1.5 text-sm">
                  <span className="font-medium">Range</span>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3"
                    value={range}
                    onChange={(e) => updateParams({ range: e.target.value })}
                    aria-label="Select time range"
                  >
                    <option value="30d">Last 30 days</option>
                    <option value="90d">Last 90 days</option>
                    <option value="180d">Last 180 days</option>
                    <option value="365d">Last 365 days</option>
                  </select>
                </label>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              <p>
                Last snapshot: {overview.freshness.lastSnapshotAt ?? '—'} · Last analysis:{' '}
                {overview.freshness.lastAnalysisAt ?? '—'}
              </p>
              {overview.freshness.neverAnalyzedRepositories.length > 0 ? (
                <p className="mt-1">
                  Never analyzed: {overview.freshness.neverAnalyzedRepositories.join(', ')}
                </p>
              ) : null}
            </CardContent>
          </Card>

          {overview.baseline.status !== 'building' ? (
            <>
              <section aria-label="Engineering trends" className="grid gap-3 xl:grid-cols-2">
                <AnalyticsTrendChart
                  title="Engineering health over time"
                  data={overview.healthTrend}
                  summary={buildTrendSummary('Engineering health', overview.healthTrend)}
                  emptyMessage={
                    canShowTrends
                      ? 'No health snapshots in the selected range.'
                      : 'Run another analysis to start measuring health change.'
                  }
                />
                <AnalyticsTrendChart
                  title="Security score over time"
                  data={overview.securityTrend}
                  summary={buildTrendSummary('Security score', overview.securityTrend)}
                />
                <AnalyticsTrendChart
                  title="Quality score over time"
                  data={overview.qualityTrend}
                  summary={buildTrendSummary('Quality score', overview.qualityTrend)}
                />
                <AnalyticsTrendChart
                  title="Dependency score over time"
                  data={overview.dependencyTrend}
                  summary={buildTrendSummary('Dependency score', overview.dependencyTrend)}
                />
                <AnalyticsTrendChart
                  title="PR risk over time"
                  data={overview.riskTrend}
                  yDomain={[0, 100]}
                  summary={buildTrendSummary('PR risk', overview.riskTrend)}
                />
                <AnalyticsTrendChart
                  title="Finding severity trend"
                  data={overview.findingTrend.map((point) => ({
                    capturedAt: point.capturedAt,
                    repositoryId: point.repositoryId,
                    repositoryName: point.repositoryName,
                    value: point.total ?? null,
                  }))}
                  yDomain={[0, 100]}
                  summary={buildTrendSummary(
                    'Total findings',
                    overview.findingTrend.map((p) => ({
                      capturedAt: p.capturedAt,
                      value: p.total,
                    })),
                  )}
                />
              </section>

              <AnalyticsRepositoryComparisonTable repositories={overview.repositoryComparisons} />

              <div className="grid gap-3 xl:grid-cols-2">
                <AnalyticsChangesPanel
                  title="Regressions"
                  items={overview.regressions}
                  emptyMessage="Nothing significant has regressed."
                  tone="critical"
                />
                <AnalyticsChangesPanel
                  title="Improvements"
                  items={overview.improvements}
                  emptyMessage="No material improvements detected yet."
                  tone="healthy"
                />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Historical activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                      {overview.baseline.snapshotCount} immutable snapshot(s) recorded
                      {overview.baseline.firstCapturedAt
                        ? ` from ${new Date(overview.baseline.firstCapturedAt).toLocaleDateString()}`
                        : ''}
                      . Historical data begins from the first successful analysis snapshot.
                    </p>
                </CardContent>
              </Card>
            </>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
