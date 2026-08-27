import { Building2 } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { cn } from '@/lib/utils'

export function WorkspaceSelector({ collapsed = false }: { collapsed?: boolean }) {
  const { organization } = useAuth()

  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-md border border-sidebar-border bg-background/60 px-2.5 py-2',
        collapsed && 'justify-center px-2',
      )}
      aria-label="Current workspace"
    >
      <div className="grid size-7 shrink-0 place-items-center rounded-md border border-border bg-card text-muted-foreground">
        <Building2 className="size-3.5" aria-hidden="true" />
      </div>
      {!collapsed ? (
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-foreground">{organization?.name ?? 'Workspace'}</p>
          <p className="truncate text-[11px] text-muted-foreground">{organization?.slug ?? '—'}</p>
        </div>
      ) : null}
    </div>
  )
}
