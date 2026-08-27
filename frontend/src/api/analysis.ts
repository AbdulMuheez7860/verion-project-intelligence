import { apiRequest } from '@/api/client'
import type { DashboardResponse } from '@/types/api'

export const analysisApi = {
  dashboard: () => apiRequest<DashboardResponse>('/api/v1/dashboard'),
}
