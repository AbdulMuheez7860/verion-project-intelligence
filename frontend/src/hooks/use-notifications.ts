import { useCallback, useEffect, useState } from 'react'
import { notificationsApi } from '@/api/notifications'
import type { Notification, PaginatedResponse } from '@/types/api'

export function useNotifications(options: { page?: number; pageSize?: number; unreadOnly?: boolean } = {}) {
  const [data, setData] = useState<PaginatedResponse<Notification> | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  const load = useCallback(async () => {
    setStatus('loading')
    try {
      const result = await notificationsApi.list({
        page: options.page ?? 1,
        pageSize: options.pageSize ?? 20,
        unreadOnly: options.unreadOnly,
      })
      setData(result)
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }, [options.page, options.pageSize, options.unreadOnly])

  useEffect(() => {
    void load()
  }, [load])

  return { data, status, reload: load }
}

export function useUnreadNotificationCount(pollMs = 30000) {
  const [count, setCount] = useState(0)

  const refresh = useCallback(async () => {
    try {
      const result = await notificationsApi.unreadCount()
      setCount(result.count)
    } catch {
      setCount(0)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(), pollMs)
    return () => window.clearInterval(timer)
  }, [pollMs, refresh])

  return { count, refresh }
}
