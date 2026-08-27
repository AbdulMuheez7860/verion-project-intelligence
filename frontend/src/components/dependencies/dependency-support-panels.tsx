import type {
  DependencyRecommendation,
  EcosystemCoverage,
  UnavailableDependencyMetric,
} from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface DependencyUnavailableMetricsProps {
  metrics: UnavailableDependencyMetric[]
}

export function DependencyUnavailableMetrics({ metrics }: DependencyUnavailableMetricsProps) {
  if (!metrics.length) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Unavailable metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-muted-foreground">
          These dependency metrics are not measured by the current analysis pipeline.
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

interface DependencyEcosystemCoverageProps {
  ecosystems: EcosystemCoverage[]
}

export function DependencyEcosystemCoverage({ ecosystems }: DependencyEcosystemCoverageProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scanner coverage by ecosystem</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {ecosystems.map((eco) => (
            <li
              key={eco.key}
              className="flex flex-col gap-1 rounded-lg border border-border px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="text-sm font-medium">{eco.label}</p>
                {eco.note ? <p className="text-xs text-muted-foreground">{eco.note}</p> : null}
              </div>
              <Badge tone={eco.supported ? 'healthy' : 'neutral'}>
                {eco.supported ? 'Supported' : 'Not currently scanned'}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

interface DependencyRecommendationsProps {
  recommendations: DependencyRecommendation[]
}

export function DependencyRecommendations({ recommendations }: DependencyRecommendationsProps) {
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
