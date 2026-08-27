import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, RefreshCw, XCircle } from 'lucide-react'
import { analysisRunsApi } from '@/api/analysis-runs'
import { AnalyzerExecutionPanel } from '@/components/analysis-runs/analyzer-execution-panel'
import { SnapshotLinkagePanel } from '@/components/analysis-runs/snapshot-linkage-panel'
import { PageHeader } from '@/components/layout/page-header'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAnalysisRun } from '@/hooks/use-analysis-run'
import { usePermissions } from '@/hooks/use-permissions'
import { useToast } from '@/hooks/use-toast'
import { formatDateTime, formatDuration } from '@/lib/format-datetime'
import { ApiError } from '@/types/api'

function statusTone(status: string) {
  if (status === 'failed') return 'critical' as const
  if (status === 'running' || status === 'queued') return 'warning' as const
  if (status === 'complete') return 'healthy' as const
  return 'neutral' as const
}

export function GlobalAnalysisRunDetailPage() {
  const { analysisId = '' } = useParams()
  const navigate = useNavigate()
  const { push } = useToast()
  const { canRetry, canCancel } = usePermissions()
  const { status, data, error, refetch } = useAnalysisRun(analysisId)
  const [actionPending, setActionPending] = useState(false)

  const handleRetry = async () => {
    if (!analysisId) return
    setActionPending(true)
    try {
      const result = await analysisRunsApi.retry(analysisId)
      push({ title: 'Analysis queued', description: result.message ?? 'Retry started.', tone: 'success' })
      if (result.analysisRunId) {
        navigate(`/app/analysis-runs/${result.analysisRunId}`)
      } else {
        void refetch()
      }
    } catch (err) {
      const message = err instanceof ApiError ? `${err.message}${err.requestId ? ` (Request ID: ${err.requestId})` : ''}` : 'Retry failed.'
      push({ title: 'Retry failed', description: message, tone: 'error' })
    } finally {
      setActionPending(false)
    }
  }

  const handleCancel = async () => {
    if (!analysisId) return
    setActionPending(true)
    try {
      const result = await analysisRunsApi.cancel(analysisId)
      push({ title: 'Analysis cancelled', description: result.message ?? 'Run cancelled.', tone: 'success' })
      void refetch()
    } catch (err) {
      const message = err instanceof ApiError ? `${err.message}${err.requestId ? ` (Request ID: ${err.requestId})` : ''}` : 'Cancel failed.'
      push({ title: 'Cancel failed', description: message, tone: 'error' })
    } finally {
      setActionPending(false)
    }
  }

  if (!analysisId) {
    return <ErrorState title="Analysis run not found" description="Missing analysis run ID." />
  }

  const showRetry = canRetry && data?.capabilities.canRetry
  const showCancel = canCancel && data?.capabilities.canCancel
  const isActive = data?.status === 'queued' || data?.status === 'running'

  return (
    <div className="space-y-5">
      <Link
        to="/app/analysis-runs"
        className="inline-flex items-center text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-1 size-3" aria-hidden="true" />
        Back to analysis runs
      </Link>

      {status === 'loading' ? <LoadingState label="Loading analysis run…" /> : null}
      {status === 'error' ? (
        <ErrorState title="Analysis run not found" description={error ?? undefined} onRetry={() => void refetch()} />
      ) : null}

      {status === 'success' && data ? (
        <>
          <PageHeader
            title={`Analysis run ${data.id.slice(-8)}`}
            description={`${data.repositoryName} · ${data.status}`}
            action={
              <div className="flex flex-wrap gap-2">
                {showRetry ? (
                  <Button size="sm" variant="outline" disabled={actionPending} onClick={() => void handleRetry()}>
                    <RefreshCw className="mr-1.5 size-3.5" aria-hidden="true" />
                    Retry
                  </Button>
                ) : null}
                {showCancel ? (
                  <Button size="sm" variant="outline" disabled={actionPending} onClick={() => void handleCancel()}>
                    <XCircle className="mr-1.5 size-3.5" aria-hidden="true" />
                    Cancel
                  </Button>
                ) : null}
              </div>
            }
          />

          {isActive ? (
            <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
              Analysis is {data.status}. This page refreshes automatically every 5 seconds until the run completes.
            </p>
          ) : null}

          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Run execution</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Repository:</span>{' '}
                  <Link to={data.repositoryHref} className="font-medium hover:underline">
                    {data.repositoryName}
                  </Link>
                </p>
                <p>
                  <span className="text-muted-foreground">Status:</span>{' '}
                  <Badge tone={statusTone(data.status)}>{data.status}</Badge>
                </p>
                <p>
                  <span className="text-muted-foreground">Trigger:</span> {data.trigger}
                </p>
                <p>
                  <span className="text-muted-foreground">Branch:</span> {data.branch ?? '—'}
                </p>
                <p>
                  <span className="text-muted-foreground">Commit:</span>{' '}
                  <code className="text-xs">{data.commitSha ?? '—'}</code>
                </p>
                <p>
                  <span className="text-muted-foreground">Started:</span> {formatDateTime(data.startedAt)}
                </p>
                <p>
                  <span className="text-muted-foreground">Completed:</span> {formatDateTime(data.completedAt)}
                </p>
                <p>
                  <span className="text-muted-foreground">Duration:</span> {formatDuration(data.durationSeconds)}
                </p>
                <p>
                  <span className="text-muted-foreground">Findings generated:</span> {data.findingCount}
                </p>
              </CardContent>
            </Card>

            <AnalyzerExecutionPanel summary={data.analyzerSummary} />
          </div>

          {data.findingsByCategory ? (
            <Card>
              <CardHeader>
                <CardTitle>Findings summary</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2 text-sm">
                {Object.entries(data.findingsByCategory).map(([category, count]) => (
                  <Badge key={category} tone="neutral">
                    {category}: {count}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <SnapshotLinkagePanel snapshot={data.snapshot} analyticsHref={data.analyticsHref} />

          {data.error ? (
            <Card>
              <CardHeader>
                <CardTitle>Error</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-destructive">{data.error}</CardContent>
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
