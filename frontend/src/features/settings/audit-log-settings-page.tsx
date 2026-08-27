import { useCallback, useEffect, useState } from 'react'
import { auditLogsApi } from '@/api/organization'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { TablePagination } from '@/components/tables/table-pagination'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AuditLog, PaginatedResponse } from '@/types/api'

export function AuditLogSettingsPage() {
  const [page, setPage] = useState(1)
  const [data, setData] = useState<PaginatedResponse<AuditLog> | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  const load = useCallback(async () => {
    setStatus('loading')
    try {
      const result = await auditLogsApi.list({ page, pageSize: 20 })
      setData(result)
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }, [page])

  useEffect(() => {
    void load()
  }, [load])

  if (status === 'loading') return <LoadingState label="Loading audit log…" />
  if (status === 'error') return <ErrorState title="Unable to load audit log" onRetry={() => void load()} />

  return (
    <Card>
      <CardHeader><CardTitle>Audit log</CardTitle></CardHeader>
      <CardContent>
        {data && data.items.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs text-muted-foreground">
                    <th className="px-2 py-2 font-medium">Event</th>
                    <th className="px-2 py-2 font-medium">Actor</th>
                    <th className="px-2 py-2 font-medium">Target</th>
                    <th className="px-2 py-2 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((log) => (
                    <tr key={log.id} className="border-b border-border last:border-0">
                      <td className="px-2 py-3 font-mono text-xs">{log.action}</td>
                      <td className="px-2 py-3">{log.actorName}</td>
                      <td className="px-2 py-3 text-muted-foreground">{log.resourceType ?? '—'}{log.resourceId ? ` · ${log.resourceId.slice(-6)}` : ''}</td>
                      <td className="px-2 py-3 text-muted-foreground">{log.createdAt ? new Date(log.createdAt).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <TablePagination page={data.page} pageSize={data.pageSize} total={data.total} hasNext={data.hasNext} onPageChange={setPage} label="events" />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No audit events recorded yet.</p>
        )}
      </CardContent>
    </Card>
  )
}
