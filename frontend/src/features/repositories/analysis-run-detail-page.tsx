import { Navigate, useParams } from 'react-router-dom'

/** Redirect legacy repo-scoped analysis URLs to the global analysis run detail page. */
export function AnalysisRunDetailPage() {
  const { analysisId = '' } = useParams()
  if (!analysisId) {
    return null
  }
  return <Navigate to={`/app/analysis-runs/${analysisId}`} replace />
}
