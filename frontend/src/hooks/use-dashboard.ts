import { useCallback, useEffect, useRef, useState } from 'react'
import { dashboardApi } from '@/api/dashboard'
import { isApiError, isNetworkError } from '@/api/client'
import type { DashboardSummaryResponse } from '@/types/api'

const POLL_INTERVAL_MS = 5000

export function useDashboardSummary() {
  const [data, setData] = useState<DashboardSummaryResponse | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)
  const [isUnavailable, setIsUnavailable] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const dataRef = useRef(data)
  dataRef.current = data

  const fetchSummary = useCallback(async (background = false) => {
    if (!background) {
      setStatus((current) => (current === 'success' ? current : 'loading'))
    } else {
      setIsRefreshing(true)
    }
    setError(null)
    setRequestId(null)
    setIsUnavailable(false)

    try {
      const result = await dashboardApi.summary()
      setData(result)
      setStatus('success')
      setLastUpdated(new Date())
    } catch (err) {
      if (isNetworkError(err) || (isApiError(err) && (err.status === 404 || err.status >= 500))) {
        setIsUnavailable(true)
        setData(null)
        setStatus('success')
        return
      }
      if (isApiError(err)) {
        setError(err.message)
        setRequestId(err.requestId ?? null)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Unable to load dashboard.')
      }
      setData(null)
      setStatus('error')
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void fetchSummary()
  }, [fetchSummary])

  useEffect(() => {
    if (!dataRef.current?.hasActiveAnalysis) return
    const interval = window.setInterval(() => {
      void fetchSummary(true)
    }, POLL_INTERVAL_MS)
    return () => window.clearInterval(interval)
  }, [data?.hasActiveAnalysis, fetchSummary])

  return {
    data,
    status,
    error,
    requestId,
    isUnavailable,
    lastUpdated,
    isRefreshing,
    refetch: () => fetchSummary(true),
  }
}
