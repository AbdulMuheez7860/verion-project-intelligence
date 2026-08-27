import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, FileDown, RefreshCw } from 'lucide-react'
import { isApiError } from '@/api/client'
import { repositoriesApi } from '@/api/repositories'
import { downloadRepositoryReportPdf } from '@/api/reports'
import { AssistantPanel } from '@/features/repositories/assistant-panel'
import { MetricCard } from '@/components/charts/metric-card'
import { MetricDefinition } from '@/components/dashboard/metric-definition'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/states/empty-state'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { TablePagination } from '@/components/tables/table-pagination'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useRepositoryIntelligence } from '@/hooks/use-repository-intelligence'
import { formatDateTime, formatDuration, formatRelativeTime } from '@/lib/format-datetime'
import { formatScore } from '@/lib/format-score'
import { PAGE_PURPOSE } from '@/lib/page-purpose'
import { riskLevelTone } from '@/lib/risk-tone'
import type {
  AnalysisRun,
  AnalysisRunDetail,
  Dependency,
  HealthHistoryResponse,
  PaginatedResponse,
  QualityFinding,
  RepositoryPullRequest,
  SecurityFinding,
} from '@/types/api'

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'] as const

function analysisStatusLabel(status: string) {
  switch (status) {
    case 'complete':
      return 'Completed'
    case 'running':
      return 'Running'
    case 'queued':
      return 'Queued'
    case 'failed':
      return 'Failed'
    default:
      return 'Never analyzed'
  }
}

export function RepositoryDetailPage() {
  const { id = '' } = useParams()
  const { data, status, error, refetch, isAnalyzing } = useRepositoryIntelligence(id)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  const [securityFindings, setSecurityFindings] = useState<PaginatedResponse<SecurityFinding> | null>(null)
  const [qualityFindings, setQualityFindings] = useState<PaginatedResponse<QualityFinding> | null>(null)
  const [dependencies, setDependencies] = useState<PaginatedResponse<Dependency> | null>(null)
  const [pullRequests, setPullRequests] = useState<PaginatedResponse<RepositoryPullRequest> | null>(null)
  const [analysisRuns, setAnalysisRuns] = useState<PaginatedResponse<AnalysisRun> | null>(null)
  const [latestRunDetail, setLatestRunDetail] = useState<AnalysisRunDetail | null>(null)
  const [healthHistory, setHealthHistory] = useState<HealthHistoryResponse | null>(null)

  const [securityPage, setSecurityPage] = useState(1)
  const [qualityPage, setQualityPage] = useState(1)
  const [depsPage, setDepsPage] = useState(1)
  const [prsPage, setPrsPage] = useState(1)
  const [runsPage, setRunsPage] = useState(1)

  useEffect(() => {
    if (!id || status !== 'success') return
    void repositoriesApi.listFindings(id, { page: securityPage, pageSize: 8, category: 'security' }).then(setSecurityFindings)
  }, [id, status, securityPage])

  useEffect(() => {
    if (!id || status !== 'success') return
    void repositoriesApi
      .listFindings(id, { page: qualityPage, pageSize: 8, category: 'quality' })
      .then((result) => setQualityFindings(result as PaginatedResponse<QualityFinding>))
  }, [id, status, qualityPage])

  useEffect(() => {
    if (!id || status !== 'success') return
    void repositoriesApi.listDependencies(id, depsPage, 8).then(setDependencies)
  }, [id, status, depsPage])

  useEffect(() => {
    if (!id || status !== 'success') return
    void repositoriesApi.listPullRequests(id, prsPage, 8).then(setPullRequests)
  }, [id, status, prsPage])

  useEffect(() => {
    if (!id || status !== 'success') return
    void repositoriesApi.listAnalysisRuns(id, runsPage, 8).then(setAnalysisRuns)
  }, [id, status, runsPage])

  useEffect(() => {
    // Repository/LOC/language metrics live on the analyzer summary of a
    // specific analysis run, not on the repository or intelligence
    // response, so the most recent run's detail is fetched separately.
    const latestRunId = analysisRuns?.items?.[0]?.id
    if (!id || !latestRunId) {
      setLatestRunDetail(null)
      return
    }
    void repositoriesApi.getAnalysisRun(id, latestRunId).then(setLatestRunDetail)
  }, [id, analysisRuns])

  useEffect(() => {
    if (!id || status !== 'success') return
    void repositoriesApi.getHealthHistory(id).then(setHealthHistory)
  }, [id, status])

  const handleAnalyze = async () => {
    if (!id || !data?.connection.canAnalyze) return
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      await repositoriesApi.analyze(id)
      await refetch()
    } catch (err) {
      setAnalyzeError(isApiError(err) ? err.message : 'Analysis could not be started.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!id || !repo) return
    setGeneratingReport(true)
    setReportError(null)
    try {
      await downloadRepositoryReportPdf(id, repo.name)
    } catch (err) {
      setReportError(isApiError(err) ? err.message : 'Report could not be generated.')
    } finally {
      setGeneratingReport(false)
    }
  }

  if (!id) {
    return <EmptyState title="Repository not found" description="No repository ID was provided." />
  }

  const repo = data?.repository
  const health = data?.health
  const latest = data?.latestAnalysis
  const hasCompleted = health?.hasCompletedAnalysis

  return (
    <div className="space-y-6">
      <Link to="/app/repositories" className="inline-flex items-center text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="mr-1 size-3" aria-hidden="true" />
        Back to repositories
      </Link>

      {status === 'loading' ? <LoadingState label="Loading repository intelligence…" /> : null}
      {status === 'error' ? (
        <ErrorState title="Repository not found" description={error ?? undefined} onRetry={() => void refetch()} />
      ) : null}

      {status === 'success' && repo && health && data ? (
        <>
          <header className="rounded-xl border border-border bg-card p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Repository intelligence</p>
                <PageHeader
                  title={repo.name}
                  purpose={PAGE_PURPOSE.repository}
                  description={[repo.owner, repo.defaultBranch ? `default ${repo.defaultBranch}` : null, repo.language]
                    .filter(Boolean)
                    .join(' · ')}
                />
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge tone="neutral">{analysisStatusLabel(repo.analysisStatus)}</Badge>
                  {repo.riskLevel ? <Badge tone={riskLevelTone(repo.riskLevel)}>Risk: {repo.riskLevel}</Badge> : null}
                  <span className="text-muted-foreground">
                    GitHub: {data.connection.githubStatus}
                    {data.connection.githubLogin ? ` (${data.connection.githubLogin})` : ''}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground" aria-live="polite">
                  {isAnalyzing
                    ? 'Analysis currently running — metrics will refresh automatically.'
                    : repo.lastAnalyzedAt
                      ? `Analyzed ${formatRelativeTime(repo.lastAnalyzedAt)}`
                      : 'No completed analysis'}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {repo.htmlUrl ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(repo.htmlUrl!, '_blank', 'noopener,noreferrer')}
                  >
                    <ExternalLink className="size-3.5" />
                    Open GitHub
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" disabled title="GitHub URL unavailable">
                    Open GitHub
                  </Button>
                )}
                <Button
                  size="sm"
                  onClick={() => void handleAnalyze()}
                  disabled={analyzing || isAnalyzing || !data.connection.canAnalyze}
                  title={data.connection.analyzeBlockedReason ?? undefined}
                >
                  <RefreshCw className={`size-3.5 ${analyzing || isAnalyzing ? 'animate-spin' : ''}`} />
                  {isAnalyzing ? 'Analysis running' : analyzing ? 'Starting…' : 'Analyze repository'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleGenerateReport()}
                  disabled={generatingReport || repo.analysisStatus !== 'complete'}
                  title={repo.analysisStatus !== 'complete' ? 'Run an analysis before generating a report.' : undefined}
                >
                  <FileDown className="size-3.5" />
                  {generatingReport ? 'Generating…' : 'Download report'}
                </Button>
              </div>
            </div>
            {!data.connection.canAnalyze && data.connection.analyzeBlockedReason ? (
              <p className="mt-3 text-xs text-muted-foreground">{data.connection.analyzeBlockedReason}</p>
            ) : null}
            {analyzeError ? (
              <p className="mt-2 text-xs text-destructive" role="alert">
                {analyzeError}
              </p>
            ) : null}
            {reportError ? (
              <p className="mt-2 text-xs text-destructive" role="alert">
                {reportError}
              </p>
            ) : null}
          </header>

          <section aria-labelledby="health-overview-heading">
            <h2 id="health-overview-heading" className="mb-3 text-sm font-semibold">
              Health overview
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {[
                ['Overall health', health.healthScore, health.healthDefinition],
                ['Security', health.securityScore, health.securityDefinition],
                ['Code quality', health.codeQualityScore, health.qualityDefinition],
                [
                  'Dependencies',
                  hasCompleted && health.dependencyScore != null ? health.dependencyScore : undefined,
                  health.dependencyDefinition,
                ],
                ['PR risk (avg)', health.prRiskAverage != null ? Math.round(health.prRiskAverage) : undefined, health.prRiskDefinition],
              ].map(([label, value, definition]) => (
                <div key={String(label)} className="relative">
                  <MetricCard
                    label={String(label)}
                    value={value != null && hasCompleted ? formatScore(value as number) : undefined}
                    unavailableReason={
                      String(label) === 'Dependencies' && data.dependencySummary.hasAnalysisData
                        ? 'No dependency manifest detected.'
                        : 'Unavailable until analysis completes.'
                    }
                  />
                  <div className="absolute right-3 top-3">
                    <MetricDefinition label={String(label)} definition={String(definition)} />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section aria-labelledby="analysis-status-heading" className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle id="analysis-status-heading">Analysis status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Status:</span> {analysisStatusLabel(repo.analysisStatus)}
                </p>
                {latest?.status === 'complete' ? (
                  <>
                    <p>
                      <span className="text-muted-foreground">Commit:</span>{' '}
                      <code className="text-xs">{latest.commitSha ?? '—'}</code>
                    </p>
                    <p>
                      <span className="text-muted-foreground">Branch:</span> {latest.branch ?? repo.defaultBranch ?? '—'}
                    </p>
                    <p>
                      <span className="text-muted-foreground">Started:</span> {formatDateTime(latest.startedAt)}
                    </p>
                    <p>
                      <span className="text-muted-foreground">Completed:</span> {formatDateTime(latest.completedAt)}
                    </p>
                    <p>
                      <span className="text-muted-foreground">Duration:</span> {formatDuration(latest.durationSeconds)}
                    </p>
                    <p>
                      <span className="text-muted-foreground">Trigger:</span> {latest.trigger}
                    </p>
                  </>
                ) : null}
                {latest?.status === 'failed' ? (
                  <>
                    <p className="text-destructive">Analysis failed.</p>
                    <p className="text-xs text-muted-foreground">{latest.error ?? 'No error detail recorded.'}</p>
                    <Button size="sm" className="mt-2" onClick={() => void handleAnalyze()} disabled={!data.connection.canAnalyze}>
                      Retry analysis
                    </Button>
                  </>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recommended actions</CardTitle>
              </CardHeader>
              <CardContent>
                {data.recommendedActions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No immediate actions required.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {data.recommendedActions.map((action) => (
                      <li key={action.id} className="rounded-md border border-border p-3">
                        <p className="font-medium">{action.label}</p>
                        <p className="text-xs text-muted-foreground">{action.description}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="assistant-heading">
            <h2 id="assistant-heading" className="mb-3 text-sm font-semibold">
              AI assistant
            </h2>
            <AssistantPanel repositoryId={id} />
          </section>

          <section aria-labelledby="analysis-history-heading">
            <h2 id="analysis-history-heading" className="mb-3 text-sm font-semibold">
              Analysis history
            </h2>
            <Card>
              <CardContent className="p-0">
                {analysisRuns?.items.length ? (
                  <ul>
                    {analysisRuns.items.map((run) => (
                      <li key={run.id} className="border-b border-border px-4 py-3 text-sm last:border-0">
                        <Link
                          to={`/app/analysis-runs/${run.id}`}
                          className="font-medium hover:underline"
                        >
                          Run {run.id.slice(-6)}
                        </Link>
                        <div className="mt-1 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
                          <span>Commit: {run.commitSha?.slice(0, 7) ?? '—'}</span>
                          <span>Branch: {run.branch ?? '—'}</span>
                          <span>Trigger: {run.trigger}</span>
                          <span>Duration: {formatDuration(run.durationSeconds)}</span>
                          <span>
                            Status: <Badge tone={run.status === 'failed' ? 'critical' : run.status === 'complete' ? 'healthy' : 'warning'}>{run.status}</Badge>
                          </span>
                          <span>Health: {run.healthScore != null ? Math.round(run.healthScore) : '—'}</span>
                          <span>Findings: {run.findingCount}</span>
                          <span>Started: {formatDateTime(run.startedAt)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="p-4 text-sm text-muted-foreground">No analysis runs recorded.</p>
                )}
                {analysisRuns ? (
                  <TablePagination
                    page={analysisRuns.page}
                    pageSize={analysisRuns.pageSize}
                    total={analysisRuns.total}
                    hasNext={analysisRuns.hasNext}
                    onPageChange={setRunsPage}
                    label="runs"
                  />
                ) : null}
              </CardContent>
            </Card>
          </section>

          {healthHistory ? (
            <section aria-labelledby="health-history-heading">
              <h2 id="health-history-heading" className="mb-3 text-sm font-semibold">
                Health history
              </h2>
              <Card>
                <CardContent className="p-4 text-sm">
                  {healthHistory.hasSufficientHistory ? (
                    <ul className="space-y-2">
                      {healthHistory.points.map((point) => (
                        <li key={point.analysisId} className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2 last:border-0">
                          <span>{formatDateTime(point.recordedAt)}</span>
                          <span className="font-mono tabular-nums">Health {point.healthScore ?? '—'}</span>
                          <span className="font-mono tabular-nums">Security {point.securityScore ?? '—'}</span>
                          <span className="font-mono tabular-nums">Quality {point.codeQualityScore ?? '—'}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted-foreground">{healthHistory.message}</p>
                  )}
                </CardContent>
              </Card>
            </section>
          ) : null}

          <section aria-labelledby="security-heading">
            <h2 id="security-heading" className="mb-3 text-sm font-semibold">
              Security overview
            </h2>
            <div className="mb-3 flex flex-wrap gap-2">
              {SEVERITY_ORDER.map((severity) => (
                <Badge key={severity} tone={riskLevelTone(severity)}>
                  {severity}: {data.securitySummary.severityCounts?.[severity] ?? 0}
                </Badge>
              ))}
            </div>
            <Card>
              <CardContent className="p-0">
                {securityFindings?.items.length ? (
                  <ul>
                    {securityFindings.items.map((finding) => (
                      <li key={finding.id} className="border-b border-border px-4 py-3 text-sm last:border-0">
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
                  <p className="p-4 text-sm text-muted-foreground">
                    {hasCompleted ? 'No security findings in the latest analysis.' : 'Run analysis to detect security issues.'}
                  </p>
                )}
                {securityFindings ? (
                  <TablePagination
                    page={securityFindings.page}
                    pageSize={securityFindings.pageSize}
                    total={securityFindings.total}
                    hasNext={securityFindings.hasNext}
                    onPageChange={setSecurityPage}
                    label="findings"
                  />
                ) : null}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="composition-heading">
            <h2 id="composition-heading" className="mb-3 text-sm font-semibold">
              Repository composition
            </h2>
            <Card>
              <CardContent className="space-y-3 p-4 text-sm">
                {(() => {
                  const summary = latestRunDetail?.analyzerSummary
                  const repoMetrics = summary?.repositoryMetrics

                  if (!summary) {
                    return (
                      <p className="text-muted-foreground">
                        {hasCompleted
                          ? 'Repository composition is unavailable for this analysis run.'
                          : 'Unavailable until analysis completes.'}
                      </p>
                    )
                  }

                  if (summary.repositoryMetricsStatus !== 'completed' || !repoMetrics) {
                    return (
                      <p className="text-muted-foreground">
                        Repository composition metrics are unavailable
                        {summary.repositoryMetricsError ? `: ${summary.repositoryMetricsError}` : ' for this analysis run.'}
                      </p>
                    )
                  }

                  const languages = Object.entries(repoMetrics.languageDistribution)

                  return (
                    <>
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div>
                          <p className="text-xs text-muted-foreground">Total files</p>
                          <p className="text-lg font-semibold">{repoMetrics.totalFiles.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Source files</p>
                          <p className="text-lg font-semibold">{repoMetrics.sourceFiles.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Test files</p>
                          <p className="text-lg font-semibold">{repoMetrics.testFiles.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Total LOC</p>
                          <p className="text-lg font-semibold">{repoMetrics.totalLoc.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Code LOC</p>
                          <p className="text-lg font-semibold">{repoMetrics.codeLoc.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Comment LOC</p>
                          <p className="text-lg font-semibold">{repoMetrics.commentLoc.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Comment / code ratio</p>
                          <p className="text-lg font-semibold">
                            {repoMetrics.commentToCodeRatio != null ? repoMetrics.commentToCodeRatio.toFixed(2) : '—'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Test / source ratio</p>
                          <p className="text-lg font-semibold">
                            {repoMetrics.testToSourceRatio != null ? repoMetrics.testToSourceRatio.toFixed(2) : '—'}
                          </p>
                        </div>
                      </div>

                      {languages.length > 0 ? (
                        <div>
                          <p className="mb-1 text-xs text-muted-foreground">Language distribution (by LOC)</p>
                          <ul className="space-y-1">
                            {languages.map(([language, stats]) => (
                              <li key={language} className="flex justify-between border-b border-border py-1 last:border-0">
                                <span>{language}</span>
                                <span className="text-muted-foreground">
                                  {stats.totalLoc.toLocaleString()} LOC · {stats.files.toLocaleString()} files
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {repoMetrics.truncated ? (
                        <p className="text-xs text-amber-600">
                          This repository is large enough that scanning was capped — the numbers above are a lower
                          bound, not an exact total.
                        </p>
                      ) : null}

                      <p className="text-xs text-muted-foreground">{repoMetrics.methodology}</p>
                    </>
                  )
                })()}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="quality-heading">
            <h2 id="quality-heading" className="mb-3 text-sm font-semibold">
              Code quality
            </h2>
            <Card>
              <CardContent className="space-y-3 p-4 text-sm">
                <p className="text-muted-foreground">
                  Complexity, duplication, and technical debt metrics are not available — Verion currently reports
                  findings from Ruff and ESLint only.
                </p>
                {qualityFindings?.items.length ? (
                  <ul>
                    {qualityFindings.items.map((finding) => (
                      <li key={finding.id} className="border-b border-border py-2 last:border-0">
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
                  <p className="text-muted-foreground">
                    {hasCompleted ? 'No quality findings in the latest analysis.' : 'Unavailable until analysis completes.'}
                  </p>
                )}
                {qualityFindings ? (
                  <TablePagination
                    page={qualityFindings.page}
                    pageSize={qualityFindings.pageSize}
                    total={qualityFindings.total}
                    hasNext={qualityFindings.hasNext}
                    onPageChange={setQualityPage}
                    label="findings"
                  />
                ) : null}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="dependencies-heading">
            <h2 id="dependencies-heading" className="mb-3 text-sm font-semibold">
              Dependencies
            </h2>
            <Card>
              <CardContent className="p-0 text-sm">
                <p className="border-b border-border px-4 py-3 text-xs text-muted-foreground">
                  Scans Python requirements via pip-audit when a requirements.txt manifest is present.
                </p>
                {dependencies?.items.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[640px] text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-xs text-muted-foreground">
                          <th className="px-4 py-2 font-medium">Package</th>
                          <th className="px-4 py-2 font-medium">Version</th>
                          <th className="px-4 py-2 font-medium">Latest</th>
                          <th className="px-4 py-2 font-medium">Status</th>
                          <th className="px-4 py-2 font-medium">Vulnerability</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dependencies.items.map((dep) => (
                          <tr key={dep.id} className="border-b border-border last:border-0">
                            <td className="px-4 py-2">{dep.packageName}</td>
                            <td className="px-4 py-2 font-mono text-xs">{dep.currentVersion}</td>
                            <td className="px-4 py-2 font-mono text-xs">{dep.latestVersion || 'Unknown'}</td>
                            <td className="px-4 py-2">
                              <Badge
                                tone={
                                  dep.status === 'critical'
                                    ? 'critical'
                                    : dep.status === 'vulnerable'
                                      ? 'warning'
                                      : dep.status === 'unknown'
                                        ? 'neutral'
                                        : 'healthy'
                                }
                              >
                                {dep.status === 'unknown' ? 'not scanned' : dep.status}
                              </Badge>
                            </td>
                            <td className="px-4 py-2 text-xs text-muted-foreground">{dep.vulnerability ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="p-4 text-muted-foreground">
                    {data.dependencySummary.hasAnalysisData
                      ? 'No dependencies detected.'
                      : 'Dependency scan unavailable — no supported manifest found or analysis not completed.'}
                  </p>
                )}
                {dependencies ? (
                  <TablePagination
                    page={dependencies.page}
                    pageSize={dependencies.pageSize}
                    total={dependencies.total}
                    hasNext={dependencies.hasNext}
                    onPageChange={setDepsPage}
                    label="dependencies"
                  />
                ) : null}
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="prs-heading">
            <h2 id="prs-heading" className="mb-3 text-sm font-semibold">
              Pull requests
            </h2>
            <Card>
              <CardContent className="p-0">
                {pullRequests?.items.length ? (
                  <ul>
                    {pullRequests.items.map((pr) => (
                      <li key={pr.id} className="border-b border-border px-4 py-3 text-sm last:border-0">
                        <Link to={`/app/pull-requests/${pr.id}`} className="font-medium hover:underline">
                          #{pr.id} {pr.title}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {pr.author} · {pr.status} · Risk {pr.riskScore ?? '—'} · {pr.verdictLabel}
                        </p>
                        <p className="text-xs text-muted-foreground">Updated {formatRelativeTime(pr.updatedAt)}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="p-4 text-sm text-muted-foreground">No open pull requests synced for this repository.</p>
                )}
                {pullRequests ? (
                  <TablePagination
                    page={pullRequests.page}
                    pageSize={pullRequests.pageSize}
                    total={pullRequests.total}
                    hasNext={pullRequests.hasNext}
                    onPageChange={setPrsPage}
                    label="pull requests"
                  />
                ) : null}
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </div>
  )
}
