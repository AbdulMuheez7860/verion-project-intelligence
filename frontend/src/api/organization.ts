import { apiRequest } from '@/api/client'
import type {
  AnalysisSettings,
  AuditLog,
  AuditLogListParams,
  Invitation,
  Member,
  OrganizationOverview,
  PaginatedResponse,
} from '@/types/api'

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export const organizationApi = {
  overview: () => apiRequest<OrganizationOverview>('/api/v1/organization'),

  update: (payload: { name: string }) =>
    apiRequest<OrganizationOverview>('/api/v1/organization', {
      method: 'PATCH',
      body: payload,
    }),

  members: (params: { page?: number; pageSize?: number; role?: string; q?: string } = {}) =>
    apiRequest<PaginatedResponse<Member>>(
      `/api/v1/organization/members${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        role: params.role,
        q: params.q,
      })}`,
    ),

  updateMemberRole: (membershipId: string, role: string) =>
    apiRequest<Member>(`/api/v1/organization/members/${membershipId}`, {
      method: 'PATCH',
      body: { role },
    }),

  removeMember: (membershipId: string) =>
    apiRequest<void>(`/api/v1/organization/members/${membershipId}`, { method: 'DELETE' }),

  invitations: () => apiRequest<Invitation[]>('/api/v1/organization/invitations'),

  createInvitation: (payload: { email: string; role: string }) =>
    apiRequest<Invitation>('/api/v1/organization/invitations', {
      method: 'POST',
      body: payload,
    }),

  revokeInvitation: (invitationId: string) =>
    apiRequest<Invitation>(`/api/v1/organization/invitations/${invitationId}`, { method: 'DELETE' }),

  analysisSettings: () => apiRequest<AnalysisSettings>('/api/v1/organization/analysis-settings'),
}

export const auditLogsApi = {
  list: (params: AuditLogListParams = {}) =>
    apiRequest<PaginatedResponse<AuditLog>>(
      `/api/v1/audit-logs${buildQuery({
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        q: params.q,
        action: params.action,
        actorId: params.actorId,
        resourceType: params.resourceType,
        from: params.from,
        to: params.to,
        sort: params.sort,
        order: params.order,
      })}`,
    ),
}
