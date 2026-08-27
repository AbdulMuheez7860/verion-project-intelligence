import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

export function AuthErrorAlert({
  message,
  requestId,
  className,
}: {
  message: string
  requestId?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3',
        className,
      )}
      role="alert"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-sm text-foreground">{message}</p>
        {requestId ? <p className="mt-1 font-mono text-metadata">Request ID: {requestId}</p> : null}
      </div>
    </div>
  )
}
