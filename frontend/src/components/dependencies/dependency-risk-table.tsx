import type { Dependency } from '@/types/api'
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
import { formatRelativeTime } from '@/lib/format-datetime'
import { riskLevelTone } from '@/lib/risk-tone'

interface DependencyRiskTableProps {
  dependencies: Dependency[]
  hasFilters: boolean
}

function statusTone(status: Dependency['status']) {
  switch (status) {
    case 'critical':
    case 'vulnerable':
      return 'critical' as const
    case 'outdated':
      return 'warning' as const
    default:
      return 'healthy' as const
  }
}

export function DependencyRiskTable({ dependencies, hasFilters }: DependencyRiskTableProps) {
  if (!dependencies.length) {
    return (
      <EmptyState
        title={hasFilters ? 'No dependencies match filters' : 'No dependencies tracked'}
        description={
          hasFilters
            ? 'Try adjusting search or filter criteria.'
            : 'Analyze repositories with requirements.txt to surface dependency risks.'
        }
        className="min-h-40"
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <DataTable>
        <DataTableHead>
          <tr>
            <DataTableHeaderCell>Package</DataTableHeaderCell>
            <DataTableHeaderCell>Version</DataTableHeaderCell>
            <DataTableHeaderCell>Ecosystem</DataTableHeaderCell>
            <DataTableHeaderCell>Vulnerability</DataTableHeaderCell>
            <DataTableHeaderCell>Severity</DataTableHeaderCell>
            <DataTableHeaderCell>Status</DataTableHeaderCell>
            <DataTableHeaderCell>Repository</DataTableHeaderCell>
            <DataTableHeaderCell>Source</DataTableHeaderCell>
            <DataTableHeaderCell>Analyzed</DataTableHeaderCell>
          </tr>
        </DataTableHead>
        <DataTableBody>
          {dependencies.map((dep) => (
            <DataTableRow key={dep.id}>
              <DataTableCell className="font-medium">{dep.packageName}</DataTableCell>
              <DataTableCell mono>{dep.currentVersion}</DataTableCell>
              <DataTableCell className="capitalize">{dep.ecosystem ?? 'python'}</DataTableCell>
              <DataTableCell mono>{dep.vulnerability ?? '—'}</DataTableCell>
              <DataTableCell>
                {dep.severity ? (
                  <Badge tone={riskLevelTone(dep.severity)} className="capitalize">
                    {dep.severity}
                  </Badge>
                ) : (
                  '—'
                )}
              </DataTableCell>
              <DataTableCell>
                <Badge tone={statusTone(dep.status)} className="capitalize">
                  {dep.status}
                </Badge>
              </DataTableCell>
              <DataTableCell>{dep.repositoryName ?? '—'}</DataTableCell>
              <DataTableCell mono className="text-xs">
                {dep.source ?? 'requirements.txt'}
              </DataTableCell>
              <DataTableCell>
                {dep.analyzedAt ? formatRelativeTime(dep.analyzedAt) : '—'}
              </DataTableCell>
            </DataTableRow>
          ))}
        </DataTableBody>
      </DataTable>
    </div>
  )
}
