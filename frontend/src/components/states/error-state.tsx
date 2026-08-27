import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function ErrorState({
  title = 'Something went wrong',
  description = 'The request could not be completed.',
  requestId,
  onRetry,
  className,
}: {
  title?: string
  description?: string
  requestId?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div
      className={cn('rounded-lg border border-destructive/25 bg-destructive/5 p-6', className)}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 className="text-section-heading">{title}</h2>
          <p className="mt-2 text-supporting">{description}</p>
          {requestId ? (
            <p className="mt-3 font-mono text-metadata">
              Request ID: <span className="text-foreground">{requestId}</span>
            </p>
          ) : null}
          {onRetry ? (
            <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
