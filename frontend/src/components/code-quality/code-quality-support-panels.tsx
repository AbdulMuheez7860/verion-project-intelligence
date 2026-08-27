import type { QualityRecommendation, UnavailableQualityMetric } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface CodeQualityUnavailableMetricsProps {
  metrics: UnavailableQualityMetric[]
}

export function CodeQualityUnavailableMetrics({ metrics }: CodeQualityUnavailableMetricsProps) {
  if (!metrics.length) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Unavailable metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-muted-foreground">
          These engineering metrics are not measured by the current analysis pipeline.
        </p>
        <ul className="space-y-3">
          {metrics.map((metric) => (
            <li key={metric.key} className="rounded-lg border border-border px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">{metric.label}</p>
                <Badge tone="neutral">Not measured</Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{metric.reason}</p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

interface CodeQualityRecommendationsProps {
  recommendations: QualityRecommendation[]
}

export function CodeQualityRecommendations({ recommendations }: CodeQualityRecommendationsProps) {
  if (!recommendations.length) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommended actions</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {recommendations.map((rec) => (
            <li key={rec.id} className="rounded-lg border border-border px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">{rec.label}</p>
                <Badge
                  tone={rec.priority === 'high' ? 'critical' : rec.priority === 'medium' ? 'warning' : 'neutral'}
                  className="capitalize"
                >
                  {rec.priority}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{rec.description}</p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
