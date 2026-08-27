import { apiRequest } from '@/api/client'
import type {
  Notification,
  NotificationPreferences,
  PaginatedResponse,
} from '@/types/api'

export const notificationsApi = {
  list: (params: { page?: number; pageSize?: number; unreadOnly?: boolean; type?: string } = {}) => {
    const search = new URLSearchParams()
    if (params.page) search.set('page', String(params.page))
    if (params.pageSize) search.set('pageSize', String(params.pageSize))
    if (params.unreadOnly) search.set('unreadOnly', 'true')
    if (params.type) search.set('type', params.type)
    const query = search.toString()
    return apiRequest<PaginatedResponse<Notification>>(`/api/v1/notifications${query ? `?${query}` : ''}`)
  },

  unreadCount: () => apiRequest<{ count: number }>('/api/v1/notifications/unread-count'),

  markRead: (id: string) =>
    apiRequest<Notification>(`/api/v1/notifications/${id}/read`, { method: 'PATCH' }),

  markAllRead: () =>
    apiRequest<{ updated: number }>('/api/v1/notifications/mark-all-read', { method: 'POST' }),

  preferences: () => apiRequest<NotificationPreferences>('/api/v1/notification-preferences'),

  updatePreferences: (payload: Partial<NotificationPreferences>) =>
    apiRequest<NotificationPreferences>('/api/v1/notification-preferences', {
      method: 'PUT',
      body: payload,
    }),
}
