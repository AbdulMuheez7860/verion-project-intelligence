import { ApiError } from '@/types/api'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

/**
 * Downloads the PDF report and triggers a browser save, using a blob fetch
 * (not a plain <a href>) so auth failures and "no analysis yet" errors can
 * be surfaced in the UI instead of silently opening a broken tab.
 */
export async function downloadRepositoryReportPdf(repositoryId: string, repositoryName: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/report.pdf`, {
    method: 'GET',
    credentials: 'include',
  })

  if (!response.ok) {
    let message = response.statusText
    try {
      const body = (await response.json()) as { message?: string }
      message = body.message ?? message
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, message)
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const safeName = repositoryName.replace(/[^a-zA-Z0-9-_]/g, '-')
  const link = document.createElement('a')
  link.href = url
  link.download = `verion-report-${safeName}.pdf`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
