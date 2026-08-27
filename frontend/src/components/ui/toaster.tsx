import { AlertCircle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useToast, type ToastTone } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

const toneStyles: Record<ToastTone, string> = {
  success: 'border-success/30 bg-success/8 text-foreground',
  warning: 'border-warning/35 bg-warning/10 text-foreground',
  error: 'border-destructive/30 bg-destructive/8 text-foreground',
  info: 'border-info/30 bg-info/8 text-foreground',
}

const toneIcons: Record<ToastTone, typeof Info> = {
  success: CheckCircle2,
  warning: AlertCircle,
  error: XCircle,
  info: Info,
}

export function Toaster() {
  const { toasts, dismiss } = useToast()

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[min(100vw-2rem,24rem)] flex-col gap-2"
      aria-live="polite"
      aria-relevant="additions"
    >
      {toasts.map((toast) => {
        const Icon = toneIcons[toast.tone]
        return (
          <div
            key={toast.id}
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-elevation-2',
              toneStyles[toast.tone],
            )}
            role="status"
          >
            <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{toast.title}</p>
              {toast.description ? <p className="mt-0.5 text-xs text-muted-foreground">{toast.description}</p> : null}
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Dismiss notification"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
