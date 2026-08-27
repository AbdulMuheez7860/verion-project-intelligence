import { useCallback, useEffect, useRef, useState } from 'react'
import { analysisRunsApi } from '@/api/analysis-runs'
import type { AnalysisRunDetail } from '@/types/api'

const TERMINAL = new Set(['complete', 'failed'])

export function useAnalysisRun(analysisId: string | undefined) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [data, setData] = useState<AnalysisRunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<number | null>(null)

  const load = useCallback(async (background = false) => {
    if (!analysisId) return
    if (!background) {
      setStatus('loading')
      setError(null)
    }
    try {
      const result = await analysisRunsApi.get(analysisId)
      setData(result)
      setStatus('success')
      return result
    } catch (err) {
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Failed to load analysis run.')
      return null
    }
  }, [analysisId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (pollingRef.current) {
      window.clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    if (!data || TERMINAL.has(data.status)) return

    pollingRef.current = window.setInterval(() => {
      void load(true)
    }, 5000)

    return () => {
      if (pollingRef.current) window.clearInterval(pollingRef.current)
    }
  }, [data?.status, load])

  return { status, data, error, refetch: () => load() }
}
