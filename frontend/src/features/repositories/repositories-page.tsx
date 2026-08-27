import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Link, useNavigate } from 'react-router-dom'
import { GitBranch, Search } from 'lucide-react'
import { integrationsApi } from '@/api/integrations'
import { repositoriesApi } from '@/api/repositories'
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
import { riskLevelTone } from '@/lib/risk-tone'
import type { AnalysisStatus, PaginatedResponse, Repository, RepositorySortField, RiskLevel } from '@/types/api'

function analysisLabel(status: AnalysisStatus) {
  switch (status) {
    case 'complete':
      return 'Complete'
    case 'running':
      return 'Running'
    case 'queued':
      return 'Queued'
    case 'failed':
      return 'Failed'
    default:
      return 'Not started'
  }
}

function securityStatusLabel(score: number | null | undefined): string {
  if (score == null) return 'Unavailable'
  if (score >= 80) return 'Good'
  if (score >= 60) return 'Warning'
  return 'Poor'
}

export function RepositoriesPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const debouncedQuery = useDebouncedValue(query, 300)

  const page = Number(searchParams.get('page') ?? '1')
  const sort = (searchParams.get('sort') as RepositorySortField | null) ?? 'name'
  const order = (searchParams.get('order') as 'asc' | 'desc' | null) ?? 'asc'
  const analysisStatus = (searchParams.get('analysisStatus') as AnalysisStatus | null) ?? undefined
  const riskLevel = (searchParams.get('riskLevel') as RiskLevel | null) ?? undefined
  const securityStatus = searchParams.get('securityStatus') ?? undefined

  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [data, setData] = useState<PaginatedResponse<Repository> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [githubConnected, setGithubConnected] = useState(false)

  useEffect(() => {
    void integrationsApi.getGitHub().then((result) => {
      setGithubConnected(result.status === 'connected')
    })
  }, [])

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
      analysisStatus,
      riskLevel,
      securityStatus: securityStatus as 'good' | 'warning' | 'poor' | 'unavailable' | undefined,
      sort,
      order,
    }),
    [page, debouncedQuery, analysisStatus, riskLevel, securityStatus, sort, order],
  )

  const load = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const result = await repositoriesApi.list(listParams)
      setData(result)
      setStatus('success')
    } catch (err) {
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Failed to load repositories.')
    }
  }, [listParams])

  useEffect(() => {
    void load()
  }, [load])

  const items = data?.items ?? []
  const hasFilters = Boolean(debouncedQuery || analysisStatus || riskLevel || securityStatus)

  return (
    <div className="space-y-5">
      <PageHeader
        title="Repositories"
        purpose={PAGE_PURPOSE.repositories}
        action={
          githubConnected ? (
            <Button size="sm" onClick={() => navigate('/app/repositories/connect')}>
              <GitBranch className="size-4" />
              Connect repository
            </Button>
          ) : (
            <Button size="sm" onClick={() => navigate('/app/settings/integrations')}>
              <GitBranch className="size-4" />
              Connect GitHub
            </Button>
          )
        }
      />

      <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or owner"
            className="pl-9"
            aria-label="Search repositories"
          />
        </div>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={analysisStatus ?? ''}
          onChange={(e) => updateParams({ analysisStatus: e.target.value || undefined, page: '1' })}
          aria-label="Filter by analysis status"
        >
          <option value="">All analysis statuses</option>
          <option value="not_started">Not started</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="complete">Complete</option>
          <option value="failed">Failed</option>
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={riskLevel ?? ''}
          onChange={(e) => updateParams({ riskLevel: e.target.value || undefined, page: '1' })}
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
          value={securityStatus ?? ''}
          onChange={(e) => updateParams({ securityStatus: e.target.value || undefined, page: '1' })}
          aria-label="Filter by security status"
        >
          <option value="">All security statuses</option>
          <option value="good">Good</option>
          <option value="warning">Warning</option>
          <option value="poor">Poor</option>
          <option value="unavailable">Unavailable</option>
        </select>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs text-muted-foreground" htmlFor="repo-sort">
          Sort by
        </label>
        <select
          id="repo-sort"
          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          value={sort}
          onChange={(e) => updateParams({ sort: e.target.value, page: '1' })}
        >
          <option value="name">Repository name</option>
          <option value="health">Health</option>
          <option value="risk">Risk</option>
          <option value="last_analyzed">Last analyzed</option>
          <option value="open_pull_requests">Open PRs</option>
          <option value="security">Security score</option>
          <option value="security_findings">Security findings</option>
        </select>
        <select
          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          value={order}
          onChange={(e) => updateParams({ order: e.target.value, page: '1' })}
          aria-label="Sort order"
        >
          <option value="asc">Ascending</option>
          <option value="desc">Descending</option>
        </select>
      </div>

      {status === 'loading' ? <LoadingState label="Loading repositories…" /> : null}
      {status === 'error' ? <ErrorState description={error ?? undefined} onRetry={() => void load()} /> : null}

      {status === 'success' && items.length === 0 ? (
        <EmptyState
          title={hasFilters ? 'No repositories match your filters' : 'No repositories connected'}
          description={
            hasFilters
              ? 'Try adjusting search or filters.'
              : 'Connect a GitHub repository to begin analysis.'
          }
          action={
            <Button asChild variant="outline" size="sm">
              <Link to="/app/settings/integrations">Connect GitHub</Link>
            </Button>
          }
        />
      ) : null}

      {status === 'success' && items.length > 0 ? (
        <DataList>
          <DataListHeader className="hidden md:grid md:grid-cols-[2fr_0.7fr_0.7fr_0.7fr_0.7fr_0.8fr_1fr]">
            <span>Repository</span>
            <span>Health</span>
            <span>Risk</span>
            <span>Security</span>
            <span>Quality</span>
            <span>Open PRs</span>
            <span>Analysis</span>
          </DataListHeader>
          {items.map((repo) => (
            <Link
              key={repo.id}
              to={`/app/repositories/${repo.id}`}
              className="grid gap-2 border-b border-border px-4 py-3 text-[13px] transition-colors last:border-0 hover:bg-muted/25 focus-visible:bg-muted/25 md:grid-cols-[2fr_0.7fr_0.7fr_0.7fr_0.7fr_0.8fr_1fr] md:items-center md:gap-3"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{repo.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {repo.owner}
                  {repo.private != null ? ` · ${repo.private ? 'Private' : 'Public'}` : ''}
                  {repo.defaultBranch ? ` · ${repo.defaultBranch}` : ''}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground md:hidden">Health </span>
                {repo.healthScore != null ? (
                  <span className="font-mono font-medium tabular-nums">{repo.healthScore}</span>
                ) : (
                  <span className="text-muted-foreground">Unavailable</span>
                )}
              </div>
              <div>
                <span className="text-muted-foreground md:hidden">Risk </span>
                {repo.riskLevel ? <Badge tone={riskLevelTone(repo.riskLevel)}>{repo.riskLevel}</Badge> : '—'}
              </div>
              <div>
                <span className="text-muted-foreground md:hidden">Security </span>
                {repo.securityScore != null ? (
                  <span title={securityStatusLabel(repo.securityScore)} className="font-mono tabular-nums">
                    {repo.securityScore}
                  </span>
                ) : (
                  'Unavailable'
                )}
              </div>
              <div>
                <span className="text-muted-foreground md:hidden">Quality </span>
                {repo.codeQualityScore != null ? (
                  <span className="font-mono tabular-nums">{repo.codeQualityScore}</span>
                ) : (
                  'Unavailable'
                )}
              </div>
              <div>{repo.openPullRequests}</div>
              <div className="text-xs text-muted-foreground">
                <p>{analysisLabel(repo.analysisStatus)}</p>
                <p>{repo.lastAnalyzedAt ? formatRelativeTime(repo.lastAnalyzedAt) : 'No completed analysis'}</p>
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
              label="repositories"
            />
          ) : null}
        </DataList>
      ) : null}
    </div>
  )
}
