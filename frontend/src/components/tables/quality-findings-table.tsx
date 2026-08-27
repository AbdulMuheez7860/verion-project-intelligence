import { AnalyzeRepositoryButton } from '@/components/charts/metric-card'
import { EmptyState } from '@/components/states/empty-state'
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/tables/data-table'
import type { QualityFinding } from '@/types/api'

export function QualityFindingsTable({ findings }: { findings: QualityFinding[] }) {
  if (!findings.length) {
    return (
      <EmptyState
        title="No quality findings"
        description="Findings will appear after a code quality analysis completes."
        action={<AnalyzeRepositoryButton />}
      />
    )
  }

  return (
    <DataTable>
      <DataTableHead>
        <tr>
          <DataTableHeaderCell>Severity</DataTableHeaderCell>
          <DataTableHeaderCell>Rule</DataTableHeaderCell>
          <DataTableHeaderCell>File</DataTableHeaderCell>
          <DataTableHeaderCell align="right">Line</DataTableHeaderCell>
          <DataTableHeaderCell>Category</DataTableHeaderCell>
          <DataTableHeaderCell>Status</DataTableHeaderCell>
        </tr>
      </DataTableHead>
      <DataTableBody>
        {findings.map((finding) => (
          <DataTableRow key={finding.id}>
            <DataTableCell className="capitalize">{finding.severity}</DataTableCell>
            <DataTableCell mono>{finding.rule}</DataTableCell>
            <DataTableCell mono>{finding.file}</DataTableCell>
            <DataTableCell align="right" mono>
              {finding.line}
            </DataTableCell>
            <DataTableCell>{finding.category}</DataTableCell>
            <DataTableCell className="capitalize">{finding.status}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
