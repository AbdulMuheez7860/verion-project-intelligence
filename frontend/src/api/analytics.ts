import { apiRequest } from '@/api/client'
import type { AnalyticsOverview, AnalyticsOverviewParams, AnalyticsSummary } from '@/types/api'

function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export const analyticsApi = {
  get: (range = '30d') =>
    apiRequest<AnalyticsSummary>(`/api/v1/analytics?range=${encodeURIComponent(range)}`),
  overview: (params: AnalyticsOverviewParams = {}) =>
    apiRequest<AnalyticsOverview>(
      `/api/v1/analytics/overview${buildQuery({
        repositoryId: params.repositoryId,
        from: params.from,
        to: params.to,
      })}`,
    ),
}
