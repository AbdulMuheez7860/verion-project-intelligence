import { apiRequest } from '@/api/client'
import type { DashboardSummaryResponse } from '@/types/api'

export const dashboardApi = {
  summary: () => apiRequest<DashboardSummaryResponse>('/api/v1/dashboard/summary'),
}
