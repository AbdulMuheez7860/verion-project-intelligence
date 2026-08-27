import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CheckCircle2, GitBranch, Loader2, Search } from 'lucide-react'
import { integrationsApi } from '@/api/integrations'
import { repositoriesApi } from '@/api/repositories'
import { isApiError, isNetworkError } from '@/api/client'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAsyncData } from '@/hooks/use-async-data'

export function ConnectRepositoryPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [connectingId, setConnectingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { status, data, error: loadError, refetch } = useAsyncData(
    () => integrationsApi.listGitHubRepositories(),
    [],
  )

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data
    return data.filter(
      (repo) =>
        repo.fullName.toLowerCase().includes(q) ||
        repo.name.toLowerCase().includes(q) ||
        repo.owner.toLowerCase().includes(q),
    )
  }, [data, query])

  const handleConnect = async (githubId: number) => {
    setError(null)
    setConnectingId(githubId)
    try {
      const repository = await repositoriesApi.connect(githubId)
      navigate(`/app/repositories/${repository.id}`)
    } catch (err) {
      if (isNetworkError(err)) {
        setError('Cannot reach the Verion API.')
      } else if (isApiError(err)) {
        setError(err.message)
      } else {
        setError('Failed to connect repository.')
      }
    } finally {
      setConnectingId(null)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="GitHub"
        title="Connect a repository"
        description="Choose a repository from your GitHub account to sync and analyze in Verion."
        action={
          <Button asChild variant="outline">
            <Link to="/app/repositories">Back to repositories</Link>
          </Button>
        }
      />

      <div className="mb-5">
        <div className="relative max-w-xl">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search GitHub repositories"
            className="pl-9"
            aria-label="Search GitHub repositories"
          />
        </div>
      </div>

      {error ? (
        <p className="mb-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {status === 'loading' ? <LoadingState label="Loading GitHub repositories…" /> : null}
      {status === 'error' ? <ErrorState description={loadError ?? undefined} onRetry={() => void refetch()} /> : null}

      {status === 'success' && filtered.length === 0 ? (
        <EmptyState
          title={data?.length ? 'No repositories match your search' : 'No GitHub repositories found'}
          description={
            data?.length
              ? 'Try a different search term.'
              : 'Connect GitHub in Settings → Integrations, then return here to select a repository.'
          }
          action={
            <Button asChild variant="outline">
              <Link to="/app/settings/integrations">Go to integrations</Link>
            </Button>
          }
        />
      ) : null}

      {status === 'success' && filtered.length > 0 ? (
        <div className="grid gap-3">
          {filtered.map((repo) => (
            <div
              key={repo.githubId}
              className="flex flex-col gap-4 rounded-xl border border-border/80 bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <GitBranch className="size-4 text-muted-foreground" aria-hidden="true" />
                  <p className="truncate text-sm font-medium">{repo.fullName}</p>
                  {repo.private ? <Badge tone="neutral">Private</Badge> : null}
                  {repo.alreadyConnected ? (
                    <Badge tone="healthy">
                      <CheckCircle2 className="size-3" />
                      Connected
                    </Badge>
                  ) : null}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {repo.language ?? 'Unknown language'}
                  {repo.defaultBranch ? ` · default: ${repo.defaultBranch}` : ''}
                </p>
              </div>
              <Button
                size="sm"
                disabled={repo.alreadyConnected || connectingId === repo.githubId}
                onClick={() => void handleConnect(repo.githubId)}
              >
                {connectingId === repo.githubId ? <Loader2 className="size-4 animate-spin" /> : null}
                {repo.alreadyConnected ? 'Connected' : 'Connect'}
              </Button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
