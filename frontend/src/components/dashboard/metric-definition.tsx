import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

export function MetricDefinition({
  label,
  definition,
  className,
}: {
  label: string
  definition: string
  className?: string
}) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground',
        className,
      )}
      aria-label={`Definition for ${label}`}
      title={definition}
    >
      <Info className="size-3.5" aria-hidden="true" />
    </button>
  )
}
