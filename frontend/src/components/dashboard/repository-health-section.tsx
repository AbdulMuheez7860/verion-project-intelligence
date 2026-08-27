import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/states/empty-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/tables/data-table'
import { formatScore } from '@/lib/format-score'
import type { RepositoryDashboardItem } from '@/types/api'

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ')
}

export function RepositoryHealthSection({ repositories }: { repositories: RepositoryDashboardItem[] }) {
  if (repositories.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Repository health</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="No repositories connected"
            description="Connect a GitHub repository to start tracking engineering health."
            action={
              <Link to="/app/repositories/connect" className="text-sm font-medium text-primary hover:underline">
                Connect repository
              </Link>
            }
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Repository health</CardTitle>
        <Link to="/app/repositories" className="text-sm font-medium text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent className="space-y-4 px-0 pb-0 sm:px-5 sm:pb-5">
        <div className="hidden md:block">
          <DataTable>
            <DataTableHead>
              <tr>
                <DataTableHeaderCell>Repository</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Health</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Security</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Quality</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Open PRs</DataTableHeaderCell>
                <DataTableHeaderCell>Status</DataTableHeaderCell>
              </tr>
            </DataTableHead>
            <DataTableBody>
              {repositories.slice(0, 8).map((repo) => (
                <DataTableRow key={repo.id}>
                  <DataTableCell>
                    <Link to={`/app/repositories/${repo.id}`} className="font-medium hover:underline">
                      {repo.name}
                    </Link>
                  </DataTableCell>
                  <DataTableCell align="right" mono>
                    {repo.healthScore != null ? formatScore(repo.healthScore) : '—'}
                  </DataTableCell>
                  <DataTableCell align="right" mono>
                    {repo.securityScore != null ? formatScore(repo.securityScore) : '—'}
                  </DataTableCell>
                  <DataTableCell align="right" mono>
                    {repo.codeQualityScore != null ? formatScore(repo.codeQualityScore) : '—'}
                  </DataTableCell>
                  <DataTableCell align="right" mono>
                    {repo.openPullRequests}
                  </DataTableCell>
                  <DataTableCell>
                    <Badge tone={repo.analysisStatus === 'failed' ? 'critical' : 'neutral'}>
                      {statusLabel(repo.analysisStatus)}
                    </Badge>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
        </div>

        <ul className="space-y-3 px-4 md:hidden">
          {repositories.slice(0, 6).map((repo) => (
            <li key={repo.id} className="rounded-lg border border-border p-4">
              <div className="flex items-start justify-between gap-3">
                <Link to={`/app/repositories/${repo.id}`} className="font-medium hover:underline">
                  {repo.name}
                </Link>
                <Badge tone={repo.analysisStatus === 'failed' ? 'critical' : 'neutral'}>
                  {statusLabel(repo.analysisStatus)}
                </Badge>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt className="text-metadata">Health</dt>
                  <dd className="font-mono tabular-nums">{repo.healthScore != null ? formatScore(repo.healthScore) : '—'}</dd>
                </div>
                <div>
                  <dt className="text-metadata">Security</dt>
                  <dd className="font-mono tabular-nums">{repo.securityScore != null ? formatScore(repo.securityScore) : '—'}</dd>
                </div>
                <div>
                  <dt className="text-metadata">Quality</dt>
                  <dd className="font-mono tabular-nums">{repo.codeQualityScore != null ? formatScore(repo.codeQualityScore) : '—'}</dd>
                </div>
                <div>
                  <dt className="text-metadata">Open PRs</dt>
                  <dd className="font-mono tabular-nums">{repo.openPullRequests}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
