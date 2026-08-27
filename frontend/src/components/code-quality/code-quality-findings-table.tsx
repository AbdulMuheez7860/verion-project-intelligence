import { Link } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import { EmptyState } from '@/components/states/empty-state'
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/tables/data-table'
import { Badge } from '@/components/ui/badge'
import type { QualityFinding } from '@/types/api'
import { riskLevelTone } from '@/lib/risk-tone'

interface CodeQualityFindingsTableProps {
  findings: QualityFinding[]
  hasFilters?: boolean
}

export function CodeQualityFindingsTable({ findings, hasFilters = false }: CodeQualityFindingsTableProps) {
  if (!findings.length) {
    return (
      <EmptyState
        title={hasFilters ? 'No findings match your filters' : 'No quality findings'}
        description={
          hasFilters
            ? 'Try adjusting search or filter criteria.'
            : 'Findings appear after Ruff or ESLint analysis completes on connected repositories.'
        }
        action={
          !hasFilters ? (
            <Link
              to="/app/repositories"
              className="inline-flex h-8 items-center rounded-md border border-border bg-background px-3 text-xs font-medium hover:bg-muted"
            >
              View repositories
            </Link>
          ) : undefined
        }
      />
    )
  }

  return (
    <DataTable>
      <DataTableHead>
        <tr>
          <DataTableHeaderCell>Severity</DataTableHeaderCell>
          <DataTableHeaderCell>Finding</DataTableHeaderCell>
          <DataTableHeaderCell>Repository</DataTableHeaderCell>
          <DataTableHeaderCell>Rule</DataTableHeaderCell>
          <DataTableHeaderCell>File</DataTableHeaderCell>
          <DataTableHeaderCell align="right">Line</DataTableHeaderCell>
          <DataTableHeaderCell>Status</DataTableHeaderCell>
          <DataTableHeaderCell align="right">Action</DataTableHeaderCell>
        </tr>
      </DataTableHead>
      <DataTableBody>
        {findings.map((finding) => (
          <DataTableRow key={finding.id}>
            <DataTableCell>
              <Badge tone={riskLevelTone(finding.severity)} className="capitalize">
                {finding.severity}
              </Badge>
            </DataTableCell>
            <DataTableCell className="font-medium">{finding.title}</DataTableCell>
            <DataTableCell>{finding.repositoryName ?? '—'}</DataTableCell>
            <DataTableCell mono>{finding.rule}</DataTableCell>
            <DataTableCell mono>{finding.file}</DataTableCell>
            <DataTableCell align="right" mono>
              {finding.line}
            </DataTableCell>
            <DataTableCell className="capitalize">{finding.status}</DataTableCell>
            <DataTableCell align="right">
              <Link
                to={`/app/security/findings/${finding.id}`}
                className="inline-flex items-center text-xs font-medium text-primary hover:underline"
              >
                Details
                <ExternalLink className="ml-1 size-3" aria-hidden="true" />
              </Link>
            </DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
