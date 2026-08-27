import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { findingsApi } from '@/api/findings'
import { CodeQualityFindingsTable } from '@/components/code-quality/code-quality-findings-table'
import { CodeQualityMetricsPanel } from '@/components/code-quality/code-quality-metrics-panel'
import { CodeQualityPostureHeader } from '@/components/code-quality/code-quality-posture-header'
import { CodeQualityRepositoryHealth } from '@/components/code-quality/code-quality-repository-health'
import { CodeQualityRulesPanel } from '@/components/code-quality/code-quality-rules-panel'
import { CodeQualitySeverityDistribution } from '@/components/code-quality/code-quality-severity-distribution'
import {
  CodeQualityRecommendations,
  CodeQualityUnavailableMetrics,
} from '@/components/code-quality/code-quality-support-panels'
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
  FindingStatus,
  PaginatedResponse,
  QualityFinding,
  QualityIntelligence,
  QualitySortField,
  RiskLevel,
} from '@/types/api'

export function CodeQualityPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const debouncedQuery = useDebouncedValue(query, 300)

  const page = Number(searchParams.get('page') ?? '1')
  const sort = (searchParams.get('sort') as QualitySortField | null) ?? 'severity'
  const order = (searchParams.get('order') as 'asc' | 'desc' | null) ?? 'desc'
  const severity = (searchParams.get('severity') as RiskLevel | null) ?? undefined
  const status = (searchParams.get('status') as FindingStatus | null) ?? undefined
  const repositoryId = searchParams.get('repositoryId') ?? undefined
  const ruleId = searchParams.get('ruleId') ?? undefined

  const [intelStatus, setIntelStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [intelligence, setIntelligence] = useState<QualityIntelligence | null>(null)
  const [intelError, setIntelError] = useState<string | null>(null)

  const [findingsStatus, setFindingsStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [findingsData, setFindingsData] = useState<PaginatedResponse<QualityFinding> | null>(null)
  const [findingsError, setFindingsError] = useState<string | null>(null)

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
      ruleId,
      sort,
      order,
    }),
    [page, debouncedQuery, repositoryId, severity, status, ruleId, sort, order],
  )

  const loadIntelligence = useCallback(async () => {
    setIntelStatus('loading')
    setIntelError(null)
    try {
      const result = await findingsApi.qualityIntelligence()
      setIntelligence(result)
      setIntelStatus('success')
    } catch (err) {
      setIntelStatus('error')
      setIntelError(err instanceof Error ? err.message : 'Failed to load code quality intelligence.')
    }
  }, [])

  const loadFindings = useCallback(async () => {
    setFindingsStatus('loading')
    setFindingsError(null)
    try {
      const result = await findingsApi.qualityFindings(listParams)
      setFindingsData(result)
      setFindingsStatus('success')
    } catch (err) {
      setFindingsStatus('error')
      setFindingsError(err instanceof Error ? err.message : 'Failed to load quality findings.')
    }
  }, [listParams])

  useEffect(() => {
    void loadIntelligence()
  }, [loadIntelligence])

  useEffect(() => {
    void loadFindings()
  }, [loadFindings])

  const hasData = intelligence?.hasAnalysisData === true
  const hasFilters = Boolean(debouncedQuery || severity || status || repositoryId || ruleId)
  const isInitialLoading = intelStatus === 'loading' && findingsStatus === 'loading' && !intelligence
  const refreshing = intelStatus === 'loading' && intelligence != null

  return (
    <div className="space-y-5">
      <PageHeader
        title="Code quality"
        purpose={PAGE_PURPOSE.codeQuality}
        description={
          hasData
            ? `${intelligence?.totals.open ?? 0} open quality finding(s) from static analysis`
            : undefined
        }
      />

      {isInitialLoading ? <LoadingState label="Loading code quality intelligence…" /> : null}
      {intelStatus === 'error' ? (
        <ErrorState description={intelError ?? undefined} onRetry={() => void loadIntelligence()} />
      ) : null}

      {intelStatus === 'success' && intelligence ? (
        <>
          {!hasData ? (
            <EmptyState
              title="Code quality intelligence unavailable"
              description="Connect repositories and run analysis to collect Ruff and ESLint quality findings."
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
              <CodeQualityPostureHeader
                posture={intelligence.posture}
                score={intelligence.score}
                freshness={intelligence.freshness}
                onRefresh={() => void loadIntelligence()}
                refreshing={refreshing}
              />

              <CodeQualityMetricsPanel
                totals={intelligence.totals}
                scannerCoverage={intelligence.scannerCoverage}
                score={intelligence.score}
                hasData={hasData}
              />

              <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
                <CodeQualitySeverityDistribution
                  counts={intelligence.severityCounts}
                  hasData={hasData}
                  total={intelligence.totals.total}
                />
                <CodeQualityUnavailableMetrics metrics={intelligence.unavailableMetrics} />
              </div>

              <div className="grid gap-3 xl:grid-cols-2">
                <CodeQualityRepositoryHealth repositories={intelligence.repositories} hasData={hasData} />
                <CodeQualityRulesPanel
                  rules={intelligence.topRules}
                  hasData={hasData}
                  onRuleSelect={(nextRuleId) => updateParams({ ruleId: nextRuleId, page: '1' })}
                />
              </div>

              <CodeQualityRecommendations recommendations={intelligence.recommendations} />

              <Card className="min-w-0">
                <CardHeader className="space-y-4">
                  <CardTitle>Quality findings</CardTitle>
                  <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto_auto_auto]">
                    <div className="relative">
                      <Search
                        className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <Input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search title, file, rule, repository"
                        className="pl-9"
                        aria-label="Search quality findings"
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
                          {repo.name} ({repo.findingCount})
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
                      value={ruleId ?? ''}
                      onChange={(e) => updateParams({ ruleId: e.target.value || undefined, page: '1' })}
                      aria-label="Filter by rule"
                    >
                      <option value="">All rules</option>
                      {intelligence.topRules.map((rule) => (
                        <option key={rule.ruleId} value={rule.ruleId}>
                          {rule.ruleId} ({rule.count})
                        </option>
                      ))}
                    </select>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={status ?? ''}
                      onChange={(e) => updateParams({ status: e.target.value || undefined, page: '1' })}
                      aria-label="Filter by status"
                    >
                      <option value="">All statuses</option>
                      <option value="open">Open</option>
                      <option value="acknowledged">Acknowledged</option>
                      <option value="resolved">Resolved</option>
                    </select>
                    <select
                      className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                      value={`${sort}:${order}`}
                      onChange={(e) => {
                        const [nextSort, nextOrder] = e.target.value.split(':') as [QualitySortField, 'asc' | 'desc']
                        updateParams({ sort: nextSort, order: nextOrder, page: '1' })
                      }}
                      aria-label="Sort findings"
                    >
                      <option value="severity:desc">Severity (high first)</option>
                      <option value="severity:asc">Severity (low first)</option>
                      <option value="created_at:desc">Newest first</option>
                      <option value="rule_id:asc">Rule (A–Z)</option>
                      <option value="file:asc">File (A–Z)</option>
                      <option value="title:asc">Title (A–Z)</option>
                    </select>
                  </div>
                </CardHeader>
                <CardContent className="px-0 pb-0">
                  {findingsStatus === 'loading' && !findingsData ? (
                    <div className="space-y-2 px-4 pb-4" role="status" aria-label="Loading findings">
                      {Array.from({ length: 5 }).map((_, index) => (
                        <Skeleton key={index} className="h-12 w-full" />
                      ))}
                    </div>
                  ) : null}
                  {findingsStatus === 'error' ? (
                    <div className="px-4 pb-4">
                      <ErrorState description={findingsError ?? undefined} onRetry={() => void loadFindings()} />
                    </div>
                  ) : null}
                  {findingsStatus === 'success' && findingsData ? (
                    <>
                      <CodeQualityFindingsTable findings={findingsData.items} hasFilters={hasFilters} />
                      <TablePagination
                        page={findingsData.page}
                        pageSize={findingsData.pageSize}
                        total={findingsData.total}
                        hasNext={findingsData.hasNext}
                        onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
                        label="findings"
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
