import { Link } from 'react-router-dom'
import type { DependencyRepositorySummary, RiskLevel } from '@/types/api'
import { EmptyState } from '@/components/states/empty-state'
import { Badge } from '@/components/ui/badge'
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
import { riskLevelTone } from '@/lib/risk-tone'

interface DependencyRepositoryHealthProps {
  repositories: DependencyRepositorySummary[]
  hasData: boolean
}

export function DependencyRepositoryHealth({ repositories, hasData }: DependencyRepositoryHealthProps) {
  const withDependencies = repositories.filter((repo) => repo.dependencyCount > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Repository impact</CardTitle>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {!hasData ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No repository dependency data"
              description="Repository dependency summaries appear after analysis completes."
              className="min-h-28"
            />
          </div>
        ) : withDependencies.length === 0 ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No dependencies tracked"
              description="Connected repositories have no requirements.txt dependencies in the latest analysis."
              className="min-h-28"
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <DataTable>
              <DataTableHead>
                <tr>
                  <DataTableHeaderCell>Repository</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Dependencies</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Vulnerable</DataTableHeaderCell>
                  <DataTableHeaderCell>Highest</DataTableHeaderCell>
                  <DataTableHeaderCell>Last analyzed</DataTableHeaderCell>
                  <DataTableHeaderCell align="right">Action</DataTableHeaderCell>
                </tr>
              </DataTableHead>
              <DataTableBody>
                {withDependencies.map((repo) => (
                  <DataTableRow key={repo.id}>
                    <DataTableCell className="font-medium">{repo.name}</DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.dependencyCount}
                    </DataTableCell>
                    <DataTableCell align="right" mono>
                      {repo.vulnerableCount}
                    </DataTableCell>
                    <DataTableCell>
                      {repo.highestSeverity ? (
                        <Badge tone={riskLevelTone(repo.highestSeverity as RiskLevel)} className="capitalize">
                          {repo.highestSeverity}
                        </Badge>
                      ) : (
                        '—'
                      )}
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
