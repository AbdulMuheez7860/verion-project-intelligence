import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function PageHeader({
  eyebrow,
  title,
  purpose,
  description,
  action,
  className,
}: {
  eyebrow?: string
  title: string
  purpose?: string
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('mb-6 flex flex-col gap-3 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between', className)}>
      <div className="min-w-0">
        {eyebrow ? <p className="text-label mb-1.5">{eyebrow}</p> : null}
        <h1 className="text-page-title">{title}</h1>
        {purpose ? (
          <p className="mt-2 text-sm font-medium text-foreground">{purpose}</p>
        ) : null}
        {description ? (
          <p className="mt-2 max-w-2xl text-page-description">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
