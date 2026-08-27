import { Link } from 'react-router-dom'
import type { HistoricalChange } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface AnalyticsChangesPanelProps {
  title: string
  items: HistoricalChange[]
  emptyMessage: string
  tone: 'critical' | 'healthy'
}

export function AnalyticsChangesPanel({ title, items, emptyMessage, tone }: AnalyticsChangesPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        ) : (
          <ul className="space-y-3">
            {items.map((item, index) => (
              <li key={`${item.metric}-${item.repositoryId}-${index}`} className="rounded-lg border border-border px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      {item.repositoryName ? `${item.label} in ${item.repositoryName}` : item.label}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.interpretation}</p>
                    {item.previous != null && item.current != null ? (
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        {item.previous} → {item.current}
                        {item.delta != null ? ` (${item.delta > 0 ? '+' : ''}${item.delta})` : ''}
                      </p>
                    ) : null}
                  </div>
                  <Badge tone={tone === 'critical' ? 'critical' : 'healthy'} className="capitalize shrink-0">
                    {item.direction}
                  </Badge>
                </div>
                {item.repositoryId ? (
                  <Link
                    to={`/app/repositories/${item.repositoryId}`}
                    className="mt-2 inline-block text-xs font-medium text-primary hover:underline"
                  >
                    View repository
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
