'use client'

import { useEffect, useState } from 'react'
import { ArrowLeft, GitPullRequest, ShieldAlert } from 'lucide-react'
import { pullRequestService } from '@/lib/api/services'
import type { PullRequest } from '@/types/verion'
import { EmptyState, LoadingState } from '@/components/states'

export function PullRequestDetail({ id }: { id: number }) {
  const [loading, setLoading] = useState(true)
  const [pullRequest, setPullRequest] = useState<PullRequest>()
  useEffect(() => {
    pullRequestService.get(id).then(setPullRequest).finally(() => setLoading(false))
  }, [id])
  if (loading) return <LoadingState label="Loading pull request analysis…" />
  if (!Number.isFinite(id) || !pullRequest) return <EmptyState title="Pull request not found" description="This pull request ID does not match a tracked Verion change." />
  return <div>
    <button onClick={() => history.back()} className="mb-5 text-xs text-muted-foreground hover:text-foreground"><ArrowLeft className="mr-1 inline size-3" />Back to pull requests</button>
    <div className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-start sm:justify-between">
      <div><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Pull request #{pullRequest.id} · {pullRequest.repositoryName}</p><h1 className="mt-2 text-2xl font-semibold tracking-tight">{pullRequest.title}</h1><p className="mt-2 text-sm text-muted-foreground">Opened by {pullRequest.author} · {pullRequest.createdAt} · {pullRequest.filesChanged} files changed</p></div>
      <span className="rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-800"><ShieldAlert className="mr-1 inline size-3.5" />{pullRequest.riskScore} / 100 risk score</span>
    </div>
    <div className="mt-6 grid gap-4 sm:grid-cols-3"><div className="rounded-xl border border-border bg-card p-4"><GitPullRequest className="size-4 text-primary" /><p className="mt-3 text-xs text-muted-foreground">Status</p><p className="mt-1 font-semibold capitalize">{pullRequest.status}</p></div><div className="rounded-xl border border-border bg-card p-4"><p className="text-xs text-muted-foreground">Coverage</p><p className="mt-1 font-mono text-2xl font-semibold">{pullRequest.coverage}%</p></div><div className="rounded-xl border border-border bg-card p-4"><p className="text-xs text-muted-foreground">Findings</p><p className="mt-1 font-mono text-2xl font-semibold">{pullRequest.issues}</p></div></div>
  </div>
}
