import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { findingsApi } from '@/api/findings'
import { FindingAIInsight } from '@/components/findings/finding-ai-insight'
import { PageHeader } from '@/components/layout/page-header'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAsyncData } from '@/hooks/use-async-data'
import { formatDateTime } from '@/lib/format-datetime'
import { riskLevelTone } from '@/lib/risk-tone'

export function FindingDetailPage() {
  const { findingId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const backHref = searchParams.get('from') === 'repository' && searchParams.get('repositoryId')
    ? `/app/repositories/${searchParams.get('repositoryId')}`
    : '/app/security'
  const backLabel = backHref.startsWith('/app/repositories') ? 'Back to repository' : 'Back to security'
  const { status, data, error, refetch } = useAsyncData(
    () => findingsApi.getFinding(findingId),
    [findingId],
    { enabled: Boolean(findingId) },
  )

  if (!findingId) {
    return <ErrorState title="Finding not found" description="No finding ID was provided." />
  }

  return (
    <div className="space-y-5">
      <Link
        to={backHref}
        className="inline-flex items-center text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-1 size-3" aria-hidden="true" />
        {backLabel}
      </Link>

      {status === 'loading' ? <LoadingState label="Loading finding…" /> : null}
      {status === 'error' ? (
        <ErrorState title="Finding not found" description={error ?? undefined} onRetry={() => void refetch()} />
      ) : null}

      {status === 'success' && data ? (
        <>
          <PageHeader
            title={data.title}
            description={[data.repositoryName, data.category, data.scannerEngine].filter(Boolean).join(' · ')}
          />
          <div className="flex flex-wrap gap-2">
            <Badge tone={riskLevelTone(data.severity)}>{data.severity}</Badge>
            <Badge tone="neutral">{data.status}</Badge>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>What was detected</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>{data.description ?? 'No description provided by the analyzer.'}</p>
                <p className="text-xs text-muted-foreground">
                  {data.category === 'secret'
                    ? 'Sensitive values are redacted in this view.'
                    : 'Evidence is shown as reported by the scanner.'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Location & rule</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">File:</span>{' '}
                  <code className="text-xs">
                    {data.file}:{data.line}
                  </code>
                </p>
                <p>
                  <span className="text-muted-foreground">Rule:</span> {data.ruleId ?? '—'}
                </p>
                <p>
                  <span className="text-muted-foreground">Analyzer:</span> {data.scannerEngine ?? '—'}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Remediation</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {data.remediation ?? 'No remediation guidance was provided for this finding.'}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p>
                <span className="text-muted-foreground">First seen:</span> {formatDateTime(data.createdAt)}
              </p>
              <p>
                <span className="text-muted-foreground">Last seen:</span> {formatDateTime(data.updatedAt ?? data.createdAt)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>AI explanation</CardTitle>
            </CardHeader>
            <CardContent>
              <FindingAIInsight finding={data} />
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  )
}
