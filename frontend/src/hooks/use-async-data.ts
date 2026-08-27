import { useCallback, useEffect, useState } from 'react'
import { isApiError, isNetworkError } from '@/api/client'

export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error'

export interface AsyncState<T> {
  status: AsyncStatus
  data: T | null
  error: string | null
  isUnavailable: boolean
  refetch: () => Promise<void>
}

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options?: { enabled?: boolean },
): AsyncState<T> {
  const enabled = options?.enabled ?? true
  const [status, setStatus] = useState<AsyncStatus>('idle')
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isUnavailable, setIsUnavailable] = useState(false)

  const refetch = useCallback(async () => {
    if (!enabled) return
    setStatus('loading')
    setError(null)
    setIsUnavailable(false)

    try {
      const result = await fetcher()
      setData(result)
      setStatus('success')
    } catch (err) {
      if (isNetworkError(err) || (isApiError(err) && (err.status === 404 || err.status >= 500))) {
        setIsUnavailable(true)
        setData(null)
        setStatus('success')
        setError(null)
        return
      }

      if (isApiError(err)) {
        setError(err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Something went wrong.')
      }
      setData(null)
      setStatus('error')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled])

  useEffect(() => {
    if (!enabled) {
      setStatus('idle')
      setData(null)
      setError(null)
      setIsUnavailable(false)
      return
    }
    void refetch()
  }, [refetch, enabled])

  return { status, data, error, isUnavailable, refetch }
}
