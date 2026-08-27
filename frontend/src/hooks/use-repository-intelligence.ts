import { useCallback, useEffect, useState } from 'react'
import { isApiError } from '@/api/client'
import { repositoriesApi } from '@/api/repositories'
import type { RepositoryIntelligence } from '@/types/api'

export function useRepositoryIntelligence(repositoryId: string) {
  const [data, setData] = useState<RepositoryIntelligence | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (!repositoryId) return
    setStatus('loading')
    setError(null)
    try {
      const result = await repositoriesApi.getIntelligence(repositoryId)
      setData(result)
      setStatus('success')
    } catch (err) {
      setData(null)
      setStatus('error')
      setError(isApiError(err) ? err.message : 'Failed to load repository intelligence.')
    }
  }, [repositoryId])

  useEffect(() => {
    void refetch()
  }, [refetch])

  const isAnalyzing =
    data?.repository.analysisStatus === 'queued' || data?.repository.analysisStatus === 'running'

  useEffect(() => {
    if (!isAnalyzing) return
    const timer = window.setInterval(() => {
      void refetch()
    }, 5000)
    return () => window.clearInterval(timer)
  }, [isAnalyzing, refetch])

  return { data, status, error, refetch, isAnalyzing }
}
