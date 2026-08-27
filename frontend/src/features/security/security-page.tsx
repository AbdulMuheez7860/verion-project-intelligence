import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { findingsApi } from '@/api/findings'
import { PageHeader } from '@/components/layout/page-header'
import { SecurityMetricsPanel } from '@/components/security/security-metrics-panel'
import { SecurityPostureHeader } from '@/components/security/security-posture-header'
import { SecuritySeverityDistribution } from '@/components/security/security-severity-distribution'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { SecurityFindingsTable } from '@/components/tables/security-findings-table'
import { TablePagination } from '@/components/tables/table-pagination'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { PAGE_PURPOSE } from '@/lib/page-purpose'
import type {
  FindingStatus,
  PaginatedResponse,
  RiskLevel,
  SecurityCategory,
  SecurityFinding,
  SecurityIntelligence,
  SecuritySortField,
} from '@/types/api'

export function SecurityPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const debouncedQuery = useDebouncedValue(query, 300)

  const page = Number(searchParams.get('page') ?? '1')
  const sort = (searchParams.get('sort') as SecuritySortField | null) ?? 'severity'
  const order = (searchParams.get('order') as 'asc' | 'desc' | null) ?? 'desc'
  const severity = (searchParams.get('severity') as RiskLevel | null) ?? undefined
  const status = (searchParams.get('status') as FindingStatus | null) ?? undefined
  const category = (searchParams.get('category') as SecurityCategory | null) ?? undefined
  const repositoryId = searchParams.get('repositoryId') ?? undefined

  const [intelStatus, setIntelStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [intelligence, setIntelligence] = useState<SecurityIntelligence | null>(null)
  const [intelError, setIntelError] = useState<string | null>(null)

  const [findingsStatus, setFindingsStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [findingsData, setFindingsData] = useState<PaginatedResponse<SecurityFinding> | null>(null)
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
      category,
      sort,
      order,
    }),
    [page, debouncedQuery, repositoryId, severity, status, category, sort, order],
  )

  const loadIntelligence = useCallback(async () => {
    setIntelStatus('loading')
    setIntelError(null)
    try {
      const result = await findingsApi.securityIntelligence()
      setIntelligence(result)
      setIntelStatus('success')
    } catch (err) {
      setIntelStatus('error')
      setIntelError(err instanceof Error ? err.message : 'Failed to load security intelligence.')
    }
  }, [])

  const loadFindings = useCallback(async () => {
    setFindingsStatus('loading')
    setFindingsError(null)
    try {
      const result = await findingsApi.securityFindings(listParams)
      setFindingsData(result)
      setFindingsStatus('success')
    } catch (err) {
      setFindingsStatus('error')
      setFindingsError(err instanceof Error ? err.message : 'Failed to load security findings.')
    }
  }, [listParams])

  useEffect(() => {
    void loadIntelligence()
  }, [loadIntelligence])

  useEffect(() => {
    void loadFindings()
  }, [loadFindings])

  const hasData = intelligence?.hasAnalysisData === true
  const hasFilters = Boolean(debouncedQuery || severity || status || category || repositoryId)
  const isInitialLoading = intelStatus === 'loading' && findingsStatus === 'loading' && !intelligence

  return (
    <div className="space-y-5">
      <PageHeader
        title="Security"
        purpose={PAGE_PURPOSE.security}
        description={
          hasData
            ? `${intelligence?.totals.open ?? 0} open finding(s) across ${intelligence?.totals.repositoriesAffected ?? 0} repositories`
            : undefined
        }
      />

      {isInitialLoading ? <LoadingState label="Loading security intelligence…" /> : null}

      {intelStatus === 'error' ? (
        <ErrorState description={intelError ?? undefined} onRetry={() => void loadIntelligence()} />
      ) : null}

      {intelStatus === 'success' && intelligence ? (
        <>
          {!hasData ? (
            <EmptyState
              title="Security intelligence unavailable"
              description="Connect repositories and run analysis to detect security vulnerabilities, secrets, and dependency risks."
              action={
                <Button asChild variant="outline" size="sm">
                  <Link to="/app/repositories">View repositories</Link>
                </Button>
              }
            />
          ) : (
            <>
              <SecurityPostureHeader
                posture={intelligence.posture}
                score={intelligence.score}
                freshness={intelligence.freshness}
              />

              <SecurityMetricsPanel
                totals={intelligence.totals}
                categoryCounts={intelligence.categoryCounts}
                scannerCoverage={intelligence.scannerCoverage}
                score={intelligence.score}
                hasData={hasData}
              />

              <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
                <Card className="min-w-0">
                  <CardHeader className="space-y-4">
                    <CardTitle>Security findings</CardTitle>
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
                          aria-label="Search security findings"
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
                        value={category ?? ''}
                        onChange={(e) => updateParams({ category: e.target.value || undefined, page: '1' })}
                        aria-label="Filter by category"
                      >
                        <option value="">All categories</option>
                        <option value="security">Code security</option>
                        <option value="secret">Secrets</option>
                        <option value="dependency">Dependencies</option>
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
                          const [nextSort, nextOrder] = e.target.value.split(':') as [SecuritySortField, 'asc' | 'desc']
                          updateParams({ sort: nextSort, order: nextOrder, page: '1' })
                        }}
                        aria-label="Sort findings"
                      >
                        <option value="severity:desc">Severity (high first)</option>
                        <option value="severity:asc">Severity (low first)</option>
                        <option value="created_at:desc">Newest first</option>
                        <option value="created_at:asc">Oldest first</option>
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
                        <SecurityFindingsTable findings={findingsData.items} hasFilters={hasFilters} />
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

                <SecuritySeverityDistribution
                  counts={intelligence.severityCounts}
                  hasData={hasData}
                  total={intelligence.totals.total}
                />
              </div>
            </>
          )}
        </>
      ) : null}
    </div>
  )
}
