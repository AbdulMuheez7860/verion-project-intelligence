import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { pullRequestsApi } from '@/api/pull-requests'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { DataList, DataListHeader } from '@/components/tables/data-table'
import { TablePagination } from '@/components/tables/table-pagination'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { formatRelativeTime } from '@/lib/format-datetime'
import { PAGE_PURPOSE } from '@/lib/page-purpose'
import { riskScoreTone } from '@/lib/risk-tone'
import type { PaginatedResponse, PRVerdict, PullRequestListItem, PullRequestSortField, PullRequestStatus, RiskLevel } from '@/types/api'

function verdictTone(verdict: PRVerdict): 'healthy' | 'warning' | 'critical' | 'neutral' {
  switch (verdict) {
    case 'safe_to_merge':
      return 'healthy'
    case 'review_recommended':
      return 'warning'
    case 'high_risk':
      return 'warning'
    case 'critical_risk':
      return 'critical'
    default:
      return 'neutral'
  }
}

export function PullRequestsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const debouncedQuery = useDebouncedValue(query, 300)

  const page = Number(searchParams.get('page') ?? '1')
  const sort = (searchParams.get('sort') as PullRequestSortField | null) ?? 'updated_at'
  const order = (searchParams.get('order') as 'asc' | 'desc' | null) ?? 'desc'
  const status = (searchParams.get('state') as PullRequestStatus | null) ?? undefined
  const riskLevel = (searchParams.get('risk') as RiskLevel | null) ?? undefined
  const verdict = (searchParams.get('verdict') as PRVerdict | null) ?? undefined
  const repositoryId = searchParams.get('repositoryId') ?? undefined

  const [statusState, setStatusState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [data, setData] = useState<PaginatedResponse<PullRequestListItem> | null>(null)
  const [error, setError] = useState<string | null>(null)

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
      status,
      riskLevel,
      verdict,
      sort,
      order,
    }),
    [page, debouncedQuery, repositoryId, status, riskLevel, verdict, sort, order],
  )

  const load = useCallback(async () => {
    setStatusState('loading')
    setError(null)
    try {
      const result = await pullRequestsApi.list(listParams)
      setData(result)
      setStatusState('success')
    } catch (err) {
      setStatusState('error')
      setError(err instanceof Error ? err.message : 'Failed to load pull requests.')
    }
  }, [listParams])

  useEffect(() => {
    void load()
  }, [load])

  const items = data?.items ?? []
  const hasFilters = Boolean(debouncedQuery || status || riskLevel || verdict || repositoryId)

  return (
    <div className="space-y-5">
      <PageHeader title="Pull requests" purpose={PAGE_PURPOSE.pullRequests} />

      <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto_auto]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search PR number, title, repository, author"
            className="pl-9"
            aria-label="Search pull requests"
          />
        </div>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={status ?? ''}
          onChange={(e) => updateParams({ state: e.target.value || undefined, page: '1' })}
          aria-label="Filter by state"
        >
          <option value="">All states</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="merged">Merged</option>
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={riskLevel ?? ''}
          onChange={(e) => updateParams({ risk: e.target.value || undefined, page: '1' })}
          aria-label="Filter by risk level"
        >
          <option value="">All risk levels</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={verdict ?? ''}
          onChange={(e) => updateParams({ verdict: e.target.value || undefined, page: '1' })}
          aria-label="Filter by verdict"
        >
          <option value="">All verdicts</option>
          <option value="safe_to_merge">Low risk</option>
          <option value="review_recommended">Review recommended</option>
          <option value="high_risk">High risk</option>
          <option value="critical_risk">Blocked</option>
          <option value="analysis_unavailable">Analysis unavailable</option>
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={sort}
          onChange={(e) => updateParams({ sort: e.target.value, page: '1' })}
          aria-label="Sort pull requests"
        >
          <option value="risk_score">Risk score</option>
          <option value="updated_at">Updated</option>
          <option value="created_at">Created</option>
          <option value="repository_name">Repository</option>
          <option value="number">PR number</option>
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-muted-foreground" htmlFor="pr-order">
          Order
        </label>
        <select
          id="pr-order"
          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          value={order}
          onChange={(e) => updateParams({ order: e.target.value, page: '1' })}
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>

      {statusState === 'loading' ? <LoadingState label="Loading pull requests…" /> : null}
      {statusState === 'error' ? <ErrorState description={error ?? undefined} onRetry={() => void load()} /> : null}

      {statusState === 'success' && items.length === 0 ? (
        <EmptyState
          title={hasFilters ? 'No pull requests match your filters' : 'No pull requests yet'}
          description={
            hasFilters
              ? 'Try adjusting search or filters.'
              : 'Open pull requests will appear here after GitHub sync and repository analysis.'
          }
          action={
            <Button variant="outline" size="sm" onClick={() => navigate('/app/repositories')}>
              View repositories
            </Button>
          }
        />
      ) : null}

      {statusState === 'success' && items.length > 0 ? (
        <DataList>
          <DataListHeader className="hidden md:grid md:grid-cols-[2fr_1fr_0.8fr_0.8fr_0.7fr_0.7fr_0.7fr_1fr]">
            <span>Pull request</span>
            <span>Repository</span>
            <span>State</span>
            <span>Verdict</span>
            <span>Risk</span>
            <span>Security</span>
            <span>Quality</span>
            <span>Updated</span>
          </DataListHeader>
          {items.map((pr) => (
            <Link
              key={pr.id}
              to={`/app/pull-requests/${pr.id}`}
              className="grid gap-2 border-b border-border px-4 py-3 text-[13px] transition-colors last:border-0 hover:bg-muted/25 focus-visible:bg-muted/25 md:grid-cols-[2fr_1fr_0.8fr_0.8fr_0.7fr_0.7fr_0.7fr_1fr] md:items-center md:gap-3"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">
                  #{pr.number ?? pr.id} {pr.title}
                </p>
                <p className="truncate text-xs text-muted-foreground">{pr.author}</p>
              </div>
              <div className="truncate text-muted-foreground">{pr.repositoryName}</div>
              <div>
                <Badge tone="neutral">{pr.draft ? 'draft' : pr.status}</Badge>
              </div>
              <div>
                <Badge tone={verdictTone(pr.verdict)}>{pr.verdictLabel}</Badge>
              </div>
              <div>
                {pr.riskScore != null ? (
                  <Badge tone={riskScoreTone(pr.riskScore)}>
                    <span className="font-mono tabular-nums">{pr.riskScore}</span>
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </div>
              <div className="font-mono tabular-nums">{pr.securityImpact}</div>
              <div className="font-mono tabular-nums">{pr.qualityImpact}</div>
              <div className="text-xs text-muted-foreground">
                <p>{formatRelativeTime(pr.updatedAt)}</p>
                <p>{pr.riskScoredAt ? `Analyzed ${formatRelativeTime(pr.riskScoredAt)}` : 'Not analyzed'}</p>
              </div>
            </Link>
          ))}
          {data ? (
            <TablePagination
              page={data.page}
              pageSize={data.pageSize}
              total={data.total}
              hasNext={data.hasNext}
              onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
              label="pull requests"
            />
          ) : null}
        </DataList>
      ) : null}
    </div>
  )
}
