import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, RefreshCw } from 'lucide-react'
import { isApiError } from '@/api/client'
import { pullRequestsApi } from '@/api/pull-requests'
import { MergeSafetyHeader } from '@/components/pull-requests/merge-safety-header'
import { RiskScoreBreakdown } from '@/components/risk/risk-score-breakdown'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAsyncData } from '@/hooks/use-async-data'
import { formatDateTime } from '@/lib/format-datetime'
import { formatScore } from '@/lib/format-score'
import { riskLevelTone } from '@/lib/risk-tone'

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'] as const

export function PullRequestDetailPage() {
  const { id } = useParams()
  const prId = Number(id)
  const isValidId = Number.isFinite(prId)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [reanalyzeError, setReanalyzeError] = useState<string | null>(null)

  const { status, data, error, refetch } = useAsyncData(
    () => pullRequestsApi.getIntelligence(prId),
    [prId],
    { enabled: isValidId },
  )

  const handleReanalyze = async () => {
    setReanalyzing(true)
    setReanalyzeError(null)
    try {
      await pullRequestsApi.reanalyze(prId)
      await refetch()
    } catch (err) {
      setReanalyzeError(isApiError(err) ? err.message : 'Re-analysis could not be started.')
    } finally {
      setReanalyzing(false)
    }
  }

  if (!isValidId) {
    return <EmptyState title="Invalid pull request" description="The pull request ID is not valid." />
  }

  const canReanalyze = data?.analysis.status !== 'running' && data?.analysis.status !== 'queued'

  return (
    <div className="space-y-6">
      <Link
        to="/app/pull-requests"
        className="inline-flex items-center text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-1 size-3" aria-hidden="true" />
        Back to pull requests
      </Link>

      {status === 'loading' ? <LoadingState label="Loading pull request intelligence…" /> : null}
      {status === 'error' ? (
        <ErrorState
          title="Pull request not found"
          description={error ?? 'This pull request could not be loaded.'}
          onRetry={() => void refetch()}
        />
      ) : null}

      {status === 'success' && data ? (
        <>
          <header className="space-y-3 rounded-xl border border-border bg-card p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Pull request intelligence</p>
                <h1 className="text-page-title">
                  #{data.number ?? data.id} {data.title}
                </h1>
                <p className="text-sm text-muted-foreground">
                  {data.repositoryName} · {data.author} · {data.changedFiles.length} files in last scored change set
                </p>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="neutral">{data.draft ? 'Draft' : data.status}</Badge>
                  {data.mergeSafety.riskLevel ? (
                    <Badge tone={riskLevelTone(data.mergeSafety.riskLevel)}>Risk: {data.mergeSafety.riskLevel}</Badge>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {data.htmlUrl ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(data.htmlUrl!, '_blank', 'noopener,noreferrer')}
                  >
                    <ExternalLink className="size-3.5" />
                    Open GitHub
                  </Button>
                ) : null}
                <Button size="sm" onClick={() => void handleReanalyze()} disabled={reanalyzing || !canReanalyze}>
                  <RefreshCw className={`size-3.5 ${reanalyzing ? 'animate-spin' : ''}`} />
                  {reanalyzing ? 'Re-analyzing…' : 'Re-analyze PR'}
                </Button>
              </div>
            </div>
            {reanalyzeError ? (
              <p className="text-xs text-destructive" role="alert">
                {reanalyzeError}
              </p>
            ) : null}
          </header>

          <MergeSafetyHeader verdict={data.mergeSafety} freshness={data.freshness} />

          {data.riskScoreDetail ? (
            <RiskScoreBreakdown risk={data.riskScoreDetail} />
          ) : (
            <EmptyState
              title="Risk breakdown unavailable"
              description="Run repository analysis and PR risk scoring to compute explainable merge factors."
            />
          )}

          <section aria-labelledby="security-impact-heading" className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle id="security-impact-heading">Security impact</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-2">
                  {SEVERITY_ORDER.map((severity) => (
                    <Badge key={severity} tone={riskLevelTone(severity)}>
                      {severity}: {data.securitySummary[severity] ?? 0}
                    </Badge>
                  ))}
                </div>
                {data.securityFindings.length ? (
                  <ul className="space-y-2">
                    {data.securityFindings.map((finding) => (
                      <li key={finding.id} className="border-b border-border pb-2 last:border-0">
                        <Link to={`/app/security/findings/${finding.id}`} className="font-medium hover:underline">
                          {finding.title}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {finding.severity} · {finding.ruleId ?? finding.category} · {finding.file}:{finding.line}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">No security findings in changed files.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Code quality impact</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  Complexity, duplication, technical debt, and coverage are unavailable — Verion reports Ruff/ESLint
                  findings in changed files only.
                </p>
                {data.qualityFindings.length ? (
                  <ul className="space-y-2">
                    {data.qualityFindings.map((finding) => (
                      <li key={finding.id} className="border-b border-border pb-2 last:border-0">
                        <Link to={`/app/security/findings/${finding.id}`} className="font-medium hover:underline">
                          {finding.title}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {finding.severity} · {finding.rule} · {finding.file}:{finding.line}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">No quality findings in changed files.</p>
                )}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="dependency-impact-heading">
            <Card>
              <CardHeader>
                <CardTitle id="dependency-impact-heading">Dependency impact</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {data.dependencyFindings.length ? (
                  <ul className="space-y-2">
                    {data.dependencyFindings.map((finding) => (
                      <li key={finding.id} className="border-b border-border pb-2 last:border-0">
                        <Link to={`/app/security/findings/${finding.id}`} className="font-medium hover:underline">
                          {finding.title}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {finding.severity} · {finding.file}:{finding.line}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">
                    No dependency vulnerabilities detected in changed files. Manifest changes are listed under changed
                    files when present.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>

          {data.repositoryHealth ? (
            <section aria-labelledby="repo-health-heading">
              <Card>
                <CardHeader>
                  <CardTitle id="repo-health-heading">Repository health context</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <p className="text-muted-foreground">Health</p>
                    <p className="font-mono tabular-nums">{formatScore(data.repositoryHealth.healthScore) ?? 'Unavailable'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Security</p>
                    <p className="font-mono tabular-nums">{formatScore(data.repositoryHealth.securityScore) ?? 'Unavailable'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Quality</p>
                    <p className="font-mono tabular-nums">
                      {formatScore(data.repositoryHealth.codeQualityScore) ?? 'Unavailable'}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Last analyzed</p>
                    <p>{formatDateTime(data.repositoryHealth.lastAnalyzedAt)}</p>
                  </div>
                  <div className="sm:col-span-2">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/app/repositories/${data.repositoryId}`}>Open repository intelligence</Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </section>
          ) : null}

          <section aria-labelledby="changed-files-heading" className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle id="changed-files-heading">Changed files</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {data.changedFiles.length ? (
                  <ul>
                    {data.changedFiles.map((file) => (
                      <li key={file.path} className="border-b border-border px-4 py-2.5 text-sm last:border-0">
                        <p className="font-mono text-xs">{file.path}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {file.status} · +{file.additions} / -{file.deletions}
                          {file.category ? ` · ${file.category}` : ''}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="p-4 text-sm text-muted-foreground">
                    Changed file details are unavailable until PR risk scoring runs with GitHub file data.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Affected areas</CardTitle>
              </CardHeader>
              <CardContent>
                {data.affectedAreas.length ? (
                  <ul className="space-y-2 text-sm">
                    {data.affectedAreas.map((area) => (
                      <li key={area.key} className="flex items-center justify-between border-b border-border py-2 last:border-0">
                        <span>{area.label}</span>
                        <span className="text-xs text-muted-foreground">
                          {area.fileCount} files · {area.findingCount} findings
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No affected areas derived from current file data.</p>
                )}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="recommendations-heading">
            <Card>
              <CardHeader>
                <CardTitle id="recommendations-heading">Recommended review actions</CardTitle>
              </CardHeader>
              <CardContent>
                {data.recommendations.length ? (
                  <ul className="space-y-2 text-sm">
                    {data.recommendations.map((action) => (
                      <li key={action.id} className="rounded-md border border-border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium">{action.label}</p>
                          <Badge tone={action.priority === 'high' ? 'critical' : action.priority === 'medium' ? 'warning' : 'neutral'}>
                            {action.priority}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{action.description}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No recommendations for this pull request.</p>
                )}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="analysis-info-heading">
            <Card>
              <CardHeader>
                <CardTitle id="analysis-info-heading">Analysis information</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
                <p>
                  <span className="text-muted-foreground">PR analysis status:</span> {data.analysis.status}
                </p>
                <p>
                  <span className="text-muted-foreground">Repository analysis:</span>{' '}
                  {data.analysis.repositoryAnalysisStatus ?? 'Unavailable'}
                </p>
                <p>
                  <span className="text-muted-foreground">Risk scored at:</span> {formatDateTime(data.analysis.riskScoredAt)}
                </p>
                <p>
                  <span className="text-muted-foreground">Head SHA:</span>{' '}
                  <code className="text-xs">{data.analysis.headSha ?? '—'}</code>
                </p>
                <p>
                  <span className="text-muted-foreground">Impact totals:</span> {data.impactCounts.total} finding(s) in
                  changed files ({data.impactCounts.security} security · {data.impactCounts.quality} quality ·{' '}
                  {data.impactCounts.dependency} dependency)
                </p>
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </div>
  )
}
