import { apiRequest } from '@/api/client'
import type {
  Dependency,
  DependencyIntelligence,
  DependencyListParams,
  DependencySummary,
  Finding,
  FindingAIExplanation,
  PaginatedResponse,
  QualityFinding,
  QualityIntelligence,
  QualityListParams,
  QualitySummary,
  SecurityFinding,
  SecurityIntelligence,
  SecurityListParams,
  SecuritySummary,
} from '@/types/api'

function buildQuery(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const search = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }

  const query = search.toString()
  return query ? `?${query}` : ''
}

export const findingsApi = {
  // ------------------------------------------------------------------
  // SECURITY
  // ------------------------------------------------------------------

  securitySummary: () =>
    apiRequest<SecuritySummary>(
      '/api/v1/findings/security/summary',
    ),

  securityIntelligence: () =>
    apiRequest<SecurityIntelligence>(
      '/api/v1/findings/security/intelligence',
    ),

  securityFindings: (params: SecurityListParams = {}) =>
    apiRequest<PaginatedResponse<SecurityFinding>>(
      `/api/v1/findings/security/findings${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        repositoryId: params.repositoryId,
        severity: params.severity,
        status: params.status,
        category: params.category,
        sort: params.sort,
        order: params.order,
      })}`,
    ),

  // ------------------------------------------------------------------
  // QUALITY
  // ------------------------------------------------------------------

  qualitySummary: () =>
    apiRequest<QualitySummary>(
      '/api/v1/findings/quality/summary',
    ),

  qualityIntelligence: () =>
    apiRequest<QualityIntelligence>(
      '/api/v1/findings/quality/intelligence',
    ),

  qualityFindings: (params: QualityListParams = {}) =>
    apiRequest<PaginatedResponse<QualityFinding>>(
      `/api/v1/findings/quality/findings${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        repositoryId: params.repositoryId,
        severity: params.severity,
        status: params.status,
        ruleId: params.ruleId,
        sort: params.sort,
        order: params.order,
      })}`,
    ),

  // Backward-compatible alias for the backend's code-quality endpoint.
  codeQualityIntelligence: () =>
    apiRequest<QualityIntelligence>(
      '/api/v1/findings/code-quality/intelligence',
    ),

  // ------------------------------------------------------------------
  // DEPENDENCIES
  // ------------------------------------------------------------------

  dependencySummary: () =>
    apiRequest<DependencySummary>(
      '/api/v1/findings/dependencies/summary',
    ),

  dependencyIntelligence: () =>
    apiRequest<DependencyIntelligence>(
      '/api/v1/findings/dependencies/intelligence',
    ),

  dependencies: (params: DependencyListParams = {}) =>
    apiRequest<PaginatedResponse<Dependency>>(
      `/api/v1/findings/dependencies${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        repositoryId: params.repositoryId,
        status: params.status,
        ecosystem: params.ecosystem,
        severity: params.severity,
        sort: params.sort,
        order: params.order,
      })}`,
    ),

  getDependency: (id: string) =>
    apiRequest<Dependency>(
      `/api/v1/findings/dependencies/${id}`,
    ),

  // ------------------------------------------------------------------
  // SINGLE FINDING
  // ------------------------------------------------------------------

  getFinding: (id: string) =>
    apiRequest<Finding>(
      `/api/v1/findings/${id}`,
    ),

  // ------------------------------------------------------------------
  // AI EXPLANATION
  // ------------------------------------------------------------------

  explainFinding: (id: string, regenerate = false) =>
    apiRequest<FindingAIExplanation>(
      `/api/v1/findings/${id}/explain${buildQuery({
        regenerate,
      })}`,
      {
        method: 'POST',
      },
    ),
}