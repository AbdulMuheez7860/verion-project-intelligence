import type { AnalyzerSummary } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface AnalyzerExecutionPanelProps {
  summary: AnalyzerSummary | null | undefined
}

export function AnalyzerExecutionPanel({ summary }: AnalyzerExecutionPanelProps) {
  if (!summary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Analyzer execution</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Analyzer summary not recorded for this run.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analyzer execution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Executed</h3>
          {summary.executed.length > 0 ? (
            <ul className="mt-2 space-y-1" aria-label="Executed analyzers">
              {summary.executed.map((name) => (
                <li key={name} className="flex items-center gap-2">
                  <span aria-hidden="true">✓</span>
                  <span>{name}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-muted-foreground">No analyzers executed.</p>
          )}
        </div>

        {summary.skipped.length > 0 ? (
          <div>
            <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Skipped</h3>
            <ul className="mt-2 space-y-2" aria-label="Skipped analyzers">
              {summary.skipped.map((item) => (
                <li key={item.name}>
                  <span className="font-medium">— {item.name}</span>
                  <p className="text-xs text-muted-foreground">{item.reason}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {summary.failed.length > 0 ? (
          <div>
            <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Failed</h3>
            <ul className="mt-2 space-y-2" aria-label="Failed analyzers">
              {summary.failed.map((item) => (
                <li key={item.name}>
                  <span className="font-medium text-destructive">✗ {item.name}</span>
                  <p className="text-xs text-muted-foreground">{item.reason}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
