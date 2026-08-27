import type { QualityRuleSummary, RiskLevel } from '@/types/api'
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
import { riskLevelTone } from '@/lib/risk-tone'

interface CodeQualityRulesPanelProps {
  rules: QualityRuleSummary[]
  hasData: boolean
  onRuleSelect?: (ruleId: string) => void
}

export function CodeQualityRulesPanel({ rules, hasData, onRuleSelect }: CodeQualityRulesPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top issue patterns</CardTitle>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {!hasData || rules.length === 0 ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No rule patterns"
              description="Frequent quality rules appear after findings are collected from Ruff and ESLint."
              className="min-h-28"
            />
          </div>
        ) : (
          <DataTable>
            <DataTableHead>
              <tr>
                <DataTableHeaderCell>Rule</DataTableHeaderCell>
                <DataTableHeaderCell>Analyzer</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Count</DataTableHeaderCell>
                <DataTableHeaderCell>Severity</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Repos</DataTableHeaderCell>
                <DataTableHeaderCell align="right">Filter</DataTableHeaderCell>
              </tr>
            </DataTableHead>
            <DataTableBody>
              {rules.map((rule) => (
                <DataTableRow key={`${rule.ruleId}-${rule.analyzer ?? 'unknown'}`}>
                  <DataTableCell mono className="font-medium">
                    {rule.ruleId}
                  </DataTableCell>
                  <DataTableCell>{rule.analyzer ?? '—'}</DataTableCell>
                  <DataTableCell align="right" mono>
                    {rule.count}
                  </DataTableCell>
                  <DataTableCell>
                    <Badge tone={riskLevelTone(rule.highestSeverity as RiskLevel)} className="capitalize">
                      {rule.highestSeverity}
                    </Badge>
                  </DataTableCell>
                  <DataTableCell align="right" mono>
                    {rule.repositoryCount}
                  </DataTableCell>
                  <DataTableCell align="right">
                    {onRuleSelect ? (
                      <button
                        type="button"
                        className="text-xs font-medium text-primary hover:underline"
                        onClick={() => onRuleSelect(rule.ruleId)}
                      >
                        View findings
                      </button>
                    ) : null}
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
