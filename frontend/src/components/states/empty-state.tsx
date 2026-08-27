import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: {
  title: string
  description: string
  action?: ReactNode
  icon?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/15 px-6 py-10 text-center',
        className,
      )}
    >
      <div className="mb-4 grid size-11 place-items-center rounded-lg border border-border bg-card text-muted-foreground">
        {icon ?? <Inbox className="size-5" aria-hidden="true" />}
      </div>
      <h2 className="text-section-heading">{title}</h2>
      <p className="mt-2 max-w-md text-supporting">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  )
}
