import { apiRequest } from '@/api/client'
import type {
  AnalysisRun,
  AnalysisRunDetail,
  Dependency,
  HealthHistoryResponse,
  PaginatedResponse,
  QualityFinding,
  Repository,
  RepositoryIntelligence,
  RepositoryListParams,
  RepositoryPullRequest,
  SecurityFinding,
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

export const repositoriesApi = {
  list: (params: RepositoryListParams = {}) =>
    apiRequest<PaginatedResponse<Repository>>(
      `/api/v1/repositories${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        analysisStatus: params.analysisStatus,
        riskLevel: params.riskLevel,
        securityStatus: params.securityStatus,
        sort: params.sort,
        order: params.order,
      })}`,
    ),

  get: (id: string) => apiRequest<Repository>(`/api/v1/repositories/${id}`),

  getIntelligence: (id: string) => apiRequest<RepositoryIntelligence>(`/api/v1/repositories/${id}/intelligence`),

  getHealthHistory: (id: string) =>
    apiRequest<HealthHistoryResponse>(`/api/v1/repositories/${id}/health-history`),

  listAnalysisRuns: (id: string, page = 1, pageSize = 10) =>
    apiRequest<PaginatedResponse<AnalysisRun>>(
      `/api/v1/repositories/${id}/analysis-runs${buildQuery({ page, pageSize })}`,
    ),

  getAnalysisRun: (repositoryId: string, analysisId: string) =>
    apiRequest<AnalysisRunDetail>(`/api/v1/repositories/${repositoryId}/analysis-runs/${analysisId}`),

  listFindings: (
    id: string,
    params: { page?: number; pageSize?: number; category?: 'security' | 'quality'; severity?: string } = {},
  ) =>
    apiRequest<PaginatedResponse<SecurityFinding | QualityFinding>>(
      `/api/v1/repositories/${id}/findings${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 10,
        category: params.category,
        severity: params.severity,
      })}`,
    ),

  listDependencies: (id: string, page = 1, pageSize = 10) =>
    apiRequest<PaginatedResponse<Dependency>>(
      `/api/v1/repositories/${id}/dependencies${buildQuery({ page, pageSize })}`,
    ),

  listPullRequests: (id: string, page = 1, pageSize = 10) =>
    apiRequest<PaginatedResponse<RepositoryPullRequest>>(
      `/api/v1/repositories/${id}/pull-requests${buildQuery({ page, pageSize })}`,
    ),

  connect: (githubId: number) =>
    apiRequest<Repository>('/api/v1/repositories', { method: 'POST', body: { githubId } }),

  disconnect: (id: string) => apiRequest<void>(`/api/v1/repositories/${id}`, { method: 'DELETE' }),

  analyze: (id: string) =>
    apiRequest<{ status: string }>(`/api/v1/repositories/${id}/analyze`, { method: 'POST' }),
}