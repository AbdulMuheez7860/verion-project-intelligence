import { apiRequest } from '@/api/client'
import type {
  AnalysisRunActionResponse,
  AnalysisRunDetail,
  AnalysisRunListParams,
  AnalysisRun,
  PaginatedResponse,
} from '@/types/api'

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export const analysisRunsApi = {
  list: (params: AnalysisRunListParams = {}) =>
    apiRequest<PaginatedResponse<AnalysisRun>>(
      `/api/v1/analysis-runs${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        repositoryId: params.repositoryId,
        status: params.status,
        trigger: params.trigger,
        from: params.from,
        to: params.to,
        sort: params.sort,
        order: params.order,
      })}`,
    ),

  get: (id: string) => apiRequest<AnalysisRunDetail>(`/api/v1/analysis-runs/${id}`),

  retry: (id: string) =>
    apiRequest<AnalysisRunActionResponse>(`/api/v1/analysis-runs/${id}/retry`, { method: 'POST' }),

  cancel: (id: string) =>
    apiRequest<AnalysisRunActionResponse>(`/api/v1/analysis-runs/${id}/cancel`, { method: 'POST' }),
}
