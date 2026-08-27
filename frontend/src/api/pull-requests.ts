import { apiRequest } from '@/api/client'
import type {
  PaginatedResponse,
  PullRequestDetail,
  PullRequestIntelligence,
  PullRequestListItem,
  PullRequestListParams,
  RiskScore,
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

export const pullRequestsApi = {
  list: (params: PullRequestListParams = {}) =>
    apiRequest<PaginatedResponse<PullRequestListItem>>(
      `/api/v1/pull-requests${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        repositoryId: params.repositoryId,
        status: params.status,
        riskLevel: params.riskLevel,
        verdict: params.verdict,
        author: params.author,
        sort: params.sort,
        order: params.order,
      })}`,
    ),

  get: (id: number) => apiRequest<PullRequestDetail>(`/api/v1/pull-requests/${id}`),

  getIntelligence: (id: number) => apiRequest<PullRequestIntelligence>(`/api/v1/pull-requests/${id}/intelligence`),

  risk: (id: number) => apiRequest<RiskScore>(`/api/v1/pull-requests/${id}/risk`),

  reanalyze: (id: number) =>
    apiRequest<{ status: string }>(`/api/v1/pull-requests/${id}/reanalyze`, { method: 'POST' }),
}
