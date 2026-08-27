import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function verdictForRisk(riskScore: number | null | undefined): {
  label: string
  detail: string
  tone: 'healthy' | 'warning' | 'critical' | 'neutral'
} {
  if (riskScore == null) {
    return {
      label: 'Cannot assess',
      detail: 'Run repository analysis to score this pull request before merging.',
      tone: 'neutral',
    }
  }
  if (riskScore >= 70) {
    return {
      label: 'High risk — review required',
      detail: 'Security findings, change size, or complexity factors exceed safe thresholds. Resolve issues before merge.',
      tone: 'critical',
    }
  }
  if (riskScore >= 50) {
    return {
      label: 'Elevated risk',
      detail: 'Multiple risk factors are present. Review the breakdown and address critical findings.',
      tone: 'critical',
    }
  }
  if (riskScore >= 30) {
    return {
      label: 'Moderate risk',
      detail: 'No critical blockers detected, but review findings in changed files before merging.',
      tone: 'warning',
    }
  }
  return {
    label: 'Low risk',
    detail: 'Current analysis shows no significant merge blockers. Standard review still applies.',
    tone: 'healthy',
  }
}

export function MergeSafetyVerdict({
  riskScore,
  findingsCount,
}: {
  riskScore: number | null | undefined
  findingsCount: number
}) {
  const verdict = verdictForRisk(riskScore)

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Merge safety</CardTitle>
        <Badge tone={verdict.tone}>{verdict.label}</Badge>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>{verdict.detail}</p>
        {riskScore != null ? (
          <p className="text-xs text-muted-foreground">
            Based on Verion Risk Engine score of{' '}
            <span className="font-mono tabular-nums">{riskScore}</span>
            {findingsCount > 0 ? ` · ${findingsCount} finding(s) in changed files` : ''}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
