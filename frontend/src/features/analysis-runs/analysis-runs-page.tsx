import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { analysisRunsApi } from '@/api/analysis-runs'
import { repositoriesApi } from '@/api/repositories'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { DataList, DataListHeader } from '@/components/tables/data-table'
import { TablePagination } from '@/components/tables/table-pagination'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { formatDateTime, formatDuration } from '@/lib/format-datetime'
import { PAGE_PURPOSE } from '@/lib/page-purpose'
import type {
  AnalysisRun,
  AnalysisRunSortField,
  AnalysisRunStatusFilter,
  AnalysisRunTriggerFilter,
  PaginatedResponse,
  Repository,
} from '@/types/api'

function statusTone(status: string) {
  if (status === 'failed') return 'critical' as const
  if (status === 'running' || status === 'queued') return 'warning' as const
  if (status === 'complete') return 'healthy' as const
  return 'neutral' as const
}

export function AnalysisRunsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const debouncedQuery = useDebouncedValue(query, 300)

  const page = Number(searchParams.get('page') ?? '1')
  const sort = (searchParams.get('sort') as AnalysisRunSortField | null) ?? 'started'
  const order = (searchParams.get('order') as 'asc' | 'desc' | null) ?? 'desc'
  const status = (searchParams.get('status') as AnalysisRunStatusFilter | null) ?? undefined
  const trigger = (searchParams.get('trigger') as AnalysisRunTriggerFilter | null) ?? undefined
  const repositoryId = searchParams.get('repositoryId') ?? undefined

  const [statusState, setStatusState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [data, setData] = useState<PaginatedResponse<AnalysisRun> | null>(null)
  const [repos, setRepos] = useState<Repository[]>([])
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
      trigger,
      sort,
      order,
    }),
    [page, debouncedQuery, repositoryId, status, trigger, sort, order],
  )

  const load = useCallback(async () => {
    setStatusState('loading')
    setError(null)
    try {
      const [runs, repoPage] = await Promise.all([
        analysisRunsApi.list(listParams),
        repositoriesApi.list({ page: 1, pageSize: 100 }),
      ])
      setData(runs)
      setRepos(repoPage.items)
      setStatusState('success')
    } catch (err) {
      setStatusState('error')
      setError(err instanceof Error ? err.message : 'Failed to load analysis runs.')
    }
  }, [listParams])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="space-y-5">
      <PageHeader
        title="Analysis runs"
        description={PAGE_PURPOSE.analysisRuns}
      />

      <DataList>
        <DataListHeader>
          <div className="grid gap-3 lg:grid-cols-[1fr_repeat(3,minmax(0,10rem))]">
            <label className="relative">
              <span className="sr-only">Search</span>
              <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search repository or commit SHA"
                className="pl-8"
                aria-label="Search analysis runs"
              />
            </label>
            <select
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              value={repositoryId ?? ''}
              onChange={(e) => updateParams({ repositoryId: e.target.value || undefined, page: '1' })}
              aria-label="Filter by repository"
            >
              <option value="">All repositories</option>
              {repos.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.fullName ?? `${repo.owner}/${repo.name}`}
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
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="complete">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <select
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              value={trigger ?? ''}
              onChange={(e) => updateParams({ trigger: e.target.value || undefined, page: '1' })}
              aria-label="Filter by trigger"
            >
              <option value="">All triggers</option>
              <option value="manual">Manual</option>
              <option value="webhook">Webhook</option>
              <option value="scheduled">Scheduled</option>
            </select>
          </div>
        </DataListHeader>

        {statusState === 'loading' ? <LoadingState label="Loading analysis runs…" /> : null}
        {statusState === 'error' ? (
          <ErrorState title="Could not load analysis runs" description={error ?? undefined} onRetry={() => void load()} />
        ) : null}

        {statusState === 'success' && data ? (
          data.items.length === 0 ? (
            <EmptyState
              title="No analysis runs"
              description="Runs appear here when repositories are analyzed."
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
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs text-muted-foreground">
                      <th className="px-4 py-2 font-medium">Repository</th>
                      <th className="px-4 py-2 font-medium">Status</th>
                      <th className="px-4 py-2 font-medium">Trigger</th>
                      <th className="px-4 py-2 font-medium">Commit</th>
                      <th className="px-4 py-2 font-medium">Health</th>
                      <th className="px-4 py-2 font-medium">Findings</th>
                      <th className="px-4 py-2 font-medium">Duration</th>
                      <th className="px-4 py-2 font-medium">Started</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((run) => (
                      <tr key={run.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-3">
                          <Link to={`/app/analysis-runs/${run.id}`} className="font-medium hover:underline">
                            {run.repositoryName ?? run.repositoryId}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={statusTone(run.status)}>{run.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{run.trigger}</td>
                        <td className="px-4 py-3 font-mono text-xs">{run.commitSha?.slice(0, 7) ?? '—'}</td>
                        <td className="px-4 py-3 font-mono tabular-nums">
                          {run.healthScore != null ? Math.round(run.healthScore) : '—'}
                        </td>
                        <td className="px-4 py-3 font-mono tabular-nums">{run.findingCount}</td>
                        <td className="px-4 py-3">{formatDuration(run.durationSeconds)}</td>
                        <td className="px-4 py-3 text-muted-foreground">{formatDateTime(run.startedAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <TablePagination
                page={data.page}
                pageSize={data.pageSize}
                total={data.total}
                hasNext={data.hasNext}
                onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
                label="runs"
              />
            </>
          )
        ) : null}
      </DataList>
    </div>
  )
}
