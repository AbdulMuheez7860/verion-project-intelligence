import { AnalyzeRepositoryButton } from '@/components/charts/metric-card'
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
import type { Dependency } from '@/types/api'

function statusTone(status: Dependency['status']): 'healthy' | 'warning' | 'critical' | 'neutral' {
  if (status === 'critical' || status === 'vulnerable') return 'critical'
  if (status === 'outdated') return 'warning'
  return 'healthy'
}

export function PackagesTable({ packages }: { packages: Dependency[] }) {
  if (!packages.length) {
    return (
      <EmptyState
        title="No dependencies tracked"
        description="Dependency data will appear after lockfile analysis completes."
        action={<AnalyzeRepositoryButton />}
      />
    )
  }

  return (
    <DataTable>
      <DataTableHead>
        <tr>
          <DataTableHeaderCell>Package</DataTableHeaderCell>
          <DataTableHeaderCell>Current</DataTableHeaderCell>
          <DataTableHeaderCell>Latest</DataTableHeaderCell>
          <DataTableHeaderCell>Status</DataTableHeaderCell>
          <DataTableHeaderCell>Vulnerability</DataTableHeaderCell>
          <DataTableHeaderCell>License</DataTableHeaderCell>
        </tr>
      </DataTableHead>
      <DataTableBody>
        {packages.map((pkg) => (
          <DataTableRow key={pkg.id}>
            <DataTableCell className="font-medium">{pkg.packageName}</DataTableCell>
            <DataTableCell mono>{pkg.currentVersion}</DataTableCell>
            <DataTableCell mono>{pkg.latestVersion}</DataTableCell>
            <DataTableCell>
              <Badge tone={statusTone(pkg.status)}>{pkg.status}</Badge>
            </DataTableCell>
            <DataTableCell mono>{pkg.vulnerability ?? 'None'}</DataTableCell>
            <DataTableCell>{pkg.license}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
