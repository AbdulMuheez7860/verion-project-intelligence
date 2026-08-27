import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { GitBranch, Loader2, Unplug } from 'lucide-react'
import { integrationsApi, type GitHubIntegration } from '@/api/integrations'
import { isApiError, isNetworkError } from '@/api/client'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { usePermissions } from '@/hooks/use-permissions'
import { useToast } from '@/hooks/use-toast'

export function IntegrationsSettingsPage() {
  const { can } = usePermissions()
  const { push } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [integration, setIntegration] = useState<GitHubIntegration | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const status = await integrationsApi.getGitHub()
      setIntegration(status)
    } catch (err) {
      if (isNetworkError(err)) {
        setError('Cannot reach the Verion API.')
      } else if (isApiError(err)) {
        setError(err.message)
      } else {
        setError('Failed to load integration status.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    const github = searchParams.get('github')
    if (github === 'connected') {
      setNotice('GitHub connected successfully.')
      push({ title: 'GitHub connected', tone: 'success' })
      void load()
      setSearchParams({}, { replace: true })
    } else if (github === 'error') {
      setError(searchParams.get('message')?.replace(/\+/g, ' ') ?? 'GitHub connection failed.')
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams, push])

  const canManage = can('integrations.manage')

  const handleConnect = async () => {
    setActionLoading(true)
    setError(null)
    try {
      const { authorizeUrl } = await integrationsApi.connectGitHub()
      window.location.href = authorizeUrl
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message)
      } else {
        setError('Unable to start GitHub OAuth.')
      }
      setActionLoading(false)
    }
  }

  const handleDisconnect = async () => {
    setActionLoading(true)
    setError(null)
    try {
      await integrationsApi.disconnectGitHub()
      setNotice('GitHub disconnected.')
      push({ title: 'Integration disconnected', tone: 'success' })
      await load()
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message)
      } else {
        setError('Unable to disconnect GitHub.')
      }
    } finally {
      setActionLoading(false)
    }
  }

  const connected = integration?.status === 'connected'

  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold">Integrations</h2>
      <p className="mt-1 text-xs text-muted-foreground">Control external connections and synchronization status.</p>

      {loading ? <LoadingState label="Loading integrations…" /> : null}
      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}
      {notice ? (
        <p className="mb-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300" role="status">
          {notice}
        </p>
      ) : null}

      {!loading && integration ? (
        <div className="mt-6 flex flex-col gap-4 rounded-xl border border-border/80 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <GitBranch className="size-5" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium">GitHub</p>
              <p className="text-xs text-muted-foreground">
                {!integration.configured
                  ? 'OAuth is not configured on the backend.'
                  : connected
                    ? `Connected as ${integration.githubLogin ?? 'unknown'} · ${integration.connectedRepositories} repositories`
                    : 'Not connected'}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={connected ? 'healthy' : 'neutral'}>{connected ? 'Connected' : 'Not connected'}</Badge>
            {connected ? (
              <>
                <Button asChild size="sm" variant="outline">
                  <Link to="/app/repositories/connect">Connect repository</Link>
                </Button>
                {canManage ? (
                  <Button size="sm" variant="outline" disabled={actionLoading} onClick={() => void handleDisconnect()}>
                    {actionLoading ? <Loader2 className="size-4 animate-spin" /> : <Unplug className="size-4" />}
                    Disconnect
                  </Button>
                ) : null}
              </>
            ) : canManage ? (
              <Button size="sm" disabled={!integration.configured || actionLoading} onClick={() => void handleConnect()}>
                {actionLoading ? <Loader2 className="size-4 animate-spin" /> : null}
                Connect GitHub
              </Button>
            ) : (
              <span className="text-xs text-muted-foreground">Admin access required to connect.</span>
            )}
          </div>
        </div>
      ) : null}
    </Card>
  )
}
