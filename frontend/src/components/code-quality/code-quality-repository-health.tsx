import { Link } from 'react-router-dom'
import type { QualityRepositorySummary, RiskLevel } from '@/types/api'
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

interface CodeQualityRepositoryHealthProps {
  repositories: QualityRepositorySummary[]
  hasData: boolean
}

export function CodeQualityRepositoryHealth({ repositories, hasData }: CodeQualityRepositoryHealthProps) {
  const affected = repositories.filter((repo) => repo.findingCount > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Repository quality</CardTitle>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {!hasData ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No repository quality data"
              description="Repository quality summaries appear after analysis completes."
              className="min-h-28"
            />
          </div>
        ) : affected.length === 0 ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No quality findings in repositories"
              description="Connected repositories have no quality findings in the latest analysis."
              className="min-h-28"
            />
          </div>
        ) : (
          <DataTable>
            <DataTableHead>
              <tr>
                <DataTableHeaderCell>Repository</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Findings</DataTableHeaderCell>
                <DataTableHeaderCell>Highest</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Score</DataTableHeaderCell>
                <DataTableHeaderCell>Last analyzed</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Action</DataTableHeaderCell>
              </tr>
            </DataTableHead>
            <DataTableBody>
              {affected.map((repo) => (
                <DataTableRow key={repo.id}>
                  <DataTableCell className="font-medium">{repo.name}</DataTableCell>
                  <DataTableCell align="right" mono>
                    {repo.openCount}/{repo.findingCount}
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
                  <DataTableCell align="right" mono>
                    {repo.qualityScore != null ? Math.round(repo.qualityScore) : '—'}
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
        )}
      </CardContent>
    </Card>
  )
}
