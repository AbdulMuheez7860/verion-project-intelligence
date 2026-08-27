import { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ExternalLink } from 'lucide-react'
import { FindingAIInsight } from '@/components/findings/finding-ai-insight'
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
import { Button } from '@/components/ui/button'
import type { SecurityFinding } from '@/types/api'
import { cn } from '@/lib/utils'
import { riskLevelTone } from '@/lib/risk-tone'

interface SecurityFindingsTableProps {
  findings: SecurityFinding[]
  hasFilters?: boolean
}

export function SecurityFindingsTable({ findings, hasFilters = false }: SecurityFindingsTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (!findings.length) {
    return (
      <EmptyState
        title={hasFilters ? 'No findings match your filters' : 'No security findings'}
        description={
          hasFilters
            ? 'Try adjusting search or filter criteria.'
            : 'Findings appear after a security analysis completes on connected repositories.'
        }
        action={
          !hasFilters ? (
            <Button asChild variant="outline" size="sm">
              <Link to="/app/repositories">View repositories</Link>
            </Button>
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
          <DataTableHeaderCell>Category</DataTableHeaderCell>
          <DataTableHeaderCell>CWE/CVE</DataTableHeaderCell>
          <DataTableHeaderCell>File</DataTableHeaderCell>
          <DataTableHeaderCell align="right">Line</DataTableHeaderCell>
          <DataTableHeaderCell>Status</DataTableHeaderCell>
          <DataTableHeaderCell align="right">Actions</DataTableHeaderCell>
        </tr>
      </DataTableHead>
      <DataTableBody>
        {findings.map((finding) => {
          const expanded = expandedId === finding.id
          return (
            <Fragment key={finding.id}>
              <DataTableRow>
                <DataTableCell>
                  <Badge tone={riskLevelTone(finding.severity)} className="capitalize">
                    {finding.severity}
                  </Badge>
                </DataTableCell>
                <DataTableCell className="font-medium">{finding.title}</DataTableCell>
                <DataTableCell>{finding.repositoryName ?? '—'}</DataTableCell>
                <DataTableCell className="capitalize">{finding.category}</DataTableCell>
                <DataTableCell mono>{finding.cwe ?? finding.cve ?? '—'}</DataTableCell>
                <DataTableCell mono>{finding.file}</DataTableCell>
                <DataTableCell align="right" mono>
                  {finding.line}
                </DataTableCell>
                <DataTableCell className="capitalize">{finding.status}</DataTableCell>
                <DataTableCell align="right">
                  <div className="flex items-center justify-end gap-2">
                    <Link
                      to={`/app/security/findings/${finding.id}`}
                      className="inline-flex items-center text-xs font-medium text-primary hover:underline"
                    >
                      Details
                      <ExternalLink className="ml-1 size-3" aria-hidden="true" />
                    </Link>
                    <button
                      type="button"
                      className="inline-flex items-center text-xs font-medium text-foreground hover:underline"
                      aria-expanded={expanded}
                      aria-label={`${expanded ? 'Hide' : 'Show'} AI explanation for ${finding.title}`}
                      onClick={() => setExpandedId(expanded ? null : finding.id)}
                    >
                      {expanded ? 'Hide' : 'Explain'}
                      <ChevronDown
                        className={cn('ml-1 size-3.5 transition-transform', expanded && 'rotate-180')}
                        aria-hidden="true"
                      />
                    </button>
                  </div>
                </DataTableCell>
              </DataTableRow>
              {expanded ? (
                <DataTableRow className="bg-muted/15 hover:bg-muted/15">
                  <DataTableCell colSpan={9} className="py-4">
                    <FindingAIInsight finding={finding} />
                  </DataTableCell>
                </DataTableRow>
              ) : null}
            </Fragment>
          )
        })}
      </DataTableBody>
    </DataTable>
  )
}
