import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { findingsApi } from '@/api/findings'
import { DependencyMetricsPanel } from '@/components/dependencies/dependency-metrics-panel'
import { DependencyPostureHeader } from '@/components/dependencies/dependency-posture-header'
import { DependencyRepositoryHealth } from '@/components/dependencies/dependency-repository-health'
import { DependencyRiskTable } from '@/components/dependencies/dependency-risk-table'
import { DependencySeverityDistribution } from '@/components/dependencies/dependency-severity-distribution'
import {
  DependencyEcosystemCoverage,
  DependencyRecommendations,
  DependencyUnavailableMetrics,
} from '@/components/dependencies/dependency-support-panels'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { TablePagination } from '@/components/tables/table-pagination'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { PAGE_PURPOSE } from '@/lib/page-purpose'
import type {
  Dependency,
  DependencyIntelligence,
  DependencySortField,
  PaginatedResponse,
  RiskLevel,
} from '@/types/api'

export function DependenciesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const debouncedQuery = useDebouncedValue(query, 300)

  const page = Number(searchParams.get('page') ?? '1')
  const sort = (searchParams.get('sort') as DependencySortField | null) ?? 'status'
  const order = (searchParams.get('order') as 'asc' | 'desc' | null) ?? 'desc'
  const severity = (searchParams.get('severity') as RiskLevel | null) ?? undefined
  const status = (searchParams.get('status') as Dependency['status'] | null) ?? undefined
  const ecosystem = (searchParams.get('ecosystem') as 'python' | null) ?? undefined
  const repositoryId = searchParams.get('repositoryId') ?? undefined

  const [intelStatus, setIntelStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [intelligence, setIntelligence] = useState<DependencyIntelligence | null>(null)
  const [intelError, setIntelError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const [depsStatus, setDepsStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [depsData, setDepsData] = useState<PaginatedResponse<Dependency> | null>(null)
  const [depsError, setDepsError] = useState<string | null>(null)

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

  useEffect(() => {
    const currentQ = searchParams.get('q') ?? ''
    if (debouncedQuery !== currentQ) {
      updateParams({ q: debouncedQuery || undefined, page: '1' })
    }
  }, [debouncedQuery, searchParams, updateParams])

  const listParams = useMemo(
    () => ({
      page,
      pageSize: 20,
      q: debouncedQuery || undefined,
      repositoryId,
      severity,
      status,
      ecosystem,
      sort,
      order,
    }),
    [page, debouncedQuery, repositoryId, severity, status, ecosystem, sort, order],
  )

  const loadIntelligence = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setIntelStatus('loading')
    setIntelError(null)
    try {
      const result = await findingsApi.dependencyIntelligence()
      setIntelligence(result)
      setIntelStatus('success')
    } catch (err) {
      setIntelStatus('error')
      setIntelError(err instanceof Error ? err.message : 'Failed to load dependency intelligence.')
    } finally {
      if (isRefresh) setRefreshing(false)
    }
  }, [])

  const loadDependencies = useCallback(async () => {
    setDepsStatus('loading')
    setDepsError(null)
    try {
      const result = await findingsApi.dependencies(listParams)
      setDepsData(result)
      setDepsStatus('success')
    } catch (err) {
      setDepsStatus('error')
      setDepsError(err instanceof Error ? err.message : 'Failed to load dependencies.')
    }
  }, [listParams])

  useEffect(() => {
    void loadIntelligence()
  }, [loadIntelligence])

  useEffect(() => {
    void loadDependencies()
  }, [loadDependencies])

  useEffect(() => {
    if (!intelligence?.freshness.analysisRunning) return
    const interval = window.setInterval(() => {
      void loadIntelligence(true)
      void loadDependencies()
    }, 10_000)
    return () => window.clearInterval(interval)
  }, [intelligence?.freshness.analysisRunning, loadIntelligence, loadDependencies])

  const hasData = intelligence?.hasAnalysisData === true
  const hasFilters = Boolean(debouncedQuery || severity || status || repositoryId || ecosystem)
  const isInitialLoading = intelStatus === 'loading' && depsStatus === 'loading' && !intelligence
  const severityTotal = intelligence?.severityCounts
    ? intelligence.severityCounts.critical +
      intelligence.severityCounts.high +
      intelligence.severityCounts.medium +
      intelligence.severityCounts.low
    : 0

  return (
    <div className="space-y-5">
      <PageHeader
        title="Dependency Intelligence"
        purpose={PAGE_PURPOSE.dependencies}
        description={
          hasData
            ? `${intelligence?.totals.total ?? 0} dependencies analyzed · ${intelligence?.totals.vulnerable ?? 0} vulnerable across ${intelligence?.totals.repositoriesAffected ?? 0} repositories`
            : undefined
        }
      />

      {isInitialLoading ? <LoadingState label="Loading dependency intelligence…" /> : null}

      {intelStatus === 'error' ? (
        <ErrorState description={intelError ?? undefined} onRetry={() => void loadIntelligence()} />
      ) : null}

      {intelStatus === 'success' && intelligence ? (
        <>
          {!hasData ? (
            <EmptyState
              title="Dependency intelligence unavailable"
              description="Connect repositories and run analysis to surface Python dependency vulnerabilities from requirements.txt."
              action={
                <Link
                  to="/app/repositories"
                  className="inline-flex h-8 items-center rounded-md border border-border bg-background px-3 text-xs font-medium hover:bg-muted"
                >
                  View repositories
                </Link>
              }
            />
          ) : (
            <>
              <DependencyPostureHeader
                posture={intelligence.posture}
                healthScore={intelligence.healthScore}
                freshness={intelligence.freshness}
                onRefresh={() => void loadIntelligence(true)}
                refreshing={refreshing}
              />

              <DependencyMetricsPanel
                totals={intelligence.totals}
                severityCounts={intelligence.severityCounts}
                scannerCoverage={intelligence.scannerCoverage}
                hasData={hasData}
              />

              <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
                <DependencySeverityDistribution
                  counts={intelligence.severityCounts}
                  hasData={hasData}
                  total={severityTotal}
                />
                <DependencyUnavailableMetrics metrics={intelligence.unavailableMetrics} />
              </div>

              <div className="grid gap-3 xl:grid-cols-2">
                <DependencyRepositoryHealth repositories={intelligence.repositories} hasData={hasData} />
                <DependencyEcosystemCoverage ecosystems={intelligence.scannerCoverage.ecosystems} />
              </div>

              <DependencyRecommendations recommendations={intelligence.recommendations} />

              <Card className="min-w-0">
                <CardHeader className="space-y-4">
                  <CardTitle>Dependency workspace</CardTitle>
                  <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto_auto_auto]">
                    <div className="relative">
                      <Search
                        className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <Input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search package, vulnerability, repository"
                        className="pl-9"
                        aria-label="Search dependencies"
                      />
                    </div>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={repositoryId ?? ''}
                      onChange={(e) => updateParams({ repositoryId: e.target.value || undefined, page: '1' })}
                      aria-label="Filter by repository"
                    >
                      <option value="">All repositories</option>
                      {intelligence.repositories.map((repo) => (
                        <option key={repo.id} value={repo.id}>
                          {repo.name} ({repo.dependencyCount})
                        </option>
                      ))}
                    </select>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={severity ?? ''}
                      onChange={(e) => updateParams({ severity: e.target.value || undefined, page: '1' })}
                      aria-label="Filter by severity"
                    >
                      <option value="">All severities</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={status ?? ''}
                      onChange={(e) => updateParams({ status: e.target.value || undefined, page: '1' })}
                      aria-label="Filter by status"
                    >
                      <option value="">All statuses</option>
                      <option value="vulnerable">Vulnerable</option>
                      <option value="critical">Critical</option>
                      <option value="healthy">Healthy</option>
                      <option value="outdated">Outdated</option>
                    </select>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={ecosystem ?? ''}
                      onChange={(e) => updateParams({ ecosystem: e.target.value || undefined, page: '1' })}
                      aria-label="Filter by ecosystem"
                    >
                      <option value="">All ecosystems</option>
                      <option value="python">Python</option>
                    </select>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={`${sort}:${order}`}
                      onChange={(e) => {
                        const [nextSort, nextOrder] = e.target.value.split(':') as [
                          DependencySortField,
                          'asc' | 'desc',
                        ]
                        updateParams({ sort: nextSort, order: nextOrder, page: '1' })
                      }}
                      aria-label="Sort dependencies"
                    >
                      <option value="status:desc">Status (risk first)</option>
                      <option value="severity:desc">Severity (high first)</option>
                      <option value="package_name:asc">Package (A–Z)</option>
                      <option value="created_at:desc">Recently analyzed</option>
                      <option value="repository_name:asc">Repository (A–Z)</option>
                    </select>
                  </div>
                </CardHeader>
                <CardContent className="px-0 pb-0">
                  {depsStatus === 'loading' && !depsData ? (
                    <div className="space-y-2 px-4 pb-4" role="status" aria-label="Loading dependencies">
                      {Array.from({ length: 5 }).map((_, index) => (
                        <Skeleton key={index} className="h-12 w-full" />
                      ))}
                    </div>
                  ) : null}
                  {depsStatus === 'error' ? (
                    <div className="px-4 pb-4">
                      <ErrorState description={depsError ?? undefined} onRetry={() => void loadDependencies()} />
                    </div>
                  ) : null}
                  {depsStatus === 'success' && depsData ? (
                    <>
                      <DependencyRiskTable dependencies={depsData.items} hasFilters={hasFilters} />
                      <TablePagination
                        page={depsData.page}
                        pageSize={depsData.pageSize}
                        total={depsData.total}
                        hasNext={depsData.hasNext}
                        onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
                        label="dependencies"
                      />
                    </>
                  ) : null}
                </CardContent>
              </Card>
            </>
          )}
        </>
      ) : null}
    </div>
  )
}
