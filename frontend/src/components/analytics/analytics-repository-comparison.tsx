import { Link } from 'react-router-dom'
import type { AnalyticsRepositoryComparison } from '@/types/api'
import { EmptyState } from '@/components/states/empty-state'
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/tables/data-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatRelativeTime } from '@/lib/format-datetime'

function trendSymbol(direction: string): string {
  switch (direction) {
    case 'improving':
      return '↑'
    case 'declining':
      return '↓'
    case 'stable':
      return '→'
    default:
      return '—'
  }
}

interface AnalyticsRepositoryComparisonTableProps {
  repositories: AnalyticsRepositoryComparison[]
}

export function AnalyticsRepositoryComparisonTable({ repositories }: AnalyticsRepositoryComparisonTableProps) {
  const rows = repositories.filter((repo) => repo.snapshotCount > 0 || repo.healthScore != null)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Repository comparison</CardTitle>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {rows.length === 0 ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No repository comparisons"
              description="Repository comparisons appear after analysis snapshots are recorded."
              className="min-h-28"
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <DataTable>
              <DataTableHead>
                <tr>
                  <DataTableHeaderCell>Repository</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Health</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Security</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Quality</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Dependencies</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">PR risk</DataTableHeaderCell>
                  <DataTableHeaderCell>Trend</DataTableHeaderCell>
                  <DataTableHeaderCell>Last analyzed</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Action</DataTableHeaderCell>
                </tr>
              </DataTableHead>
              <DataTableBody>
                {rows.map((repo) => (
                  <DataTableRow key={repo.id}>
                    <DataTableCell className="font-medium">{repo.name}</DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.healthScore != null ? Math.round(repo.healthScore) : '—'}
                    </DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.securityScore != null ? Math.round(repo.securityScore) : '—'}
                    </DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.qualityScore != null ? Math.round(repo.qualityScore) : '—'}
                    </DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.dependencyScore != null ? Math.round(repo.dependencyScore) : '—'}
                    </DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.prRiskScore != null ? Math.round(repo.prRiskScore) : '—'}
                    </DataTableCell>
                    <DataTableCell>
                      <span aria-label={`Trend ${repo.trendDirection}`}>
                        {trendSymbol(repo.trendDirection)} {repo.trendDirection}
                      </span>
                    </DataTableCell>
                    <DataTableCell>
                      {repo.lastAnalyzedAt ? formatRelativeTime(repo.lastAnalyzedAt) : '—'}
                    </DataTableCell>
                    <DataTableCell align="right">
                      <Link
                        to={`/app/repositories/${repo.id}`}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        View repo
                      </Link>
                    </DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
