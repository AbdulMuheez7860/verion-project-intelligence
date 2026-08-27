import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium leading-none',
  {
    variants: {
      tone: {
        healthy: 'border-success/30 bg-success/10 text-success',
        warning: 'border-warning/35 bg-warning/12 text-warning-foreground',
        critical: 'border-destructive/30 bg-destructive/10 text-destructive',
        info: 'border-info/30 bg-info/10 text-info',
        neutral: 'border-border bg-muted/60 text-muted-foreground',
      },
      severity: {
        critical: 'border-severity-critical/30 bg-severity-critical/10 text-severity-critical',
        high: 'border-severity-high/30 bg-severity-high/10 text-severity-high',
        medium: 'border-severity-medium/35 bg-severity-medium/12 text-severity-medium',
        low: 'border-severity-low/30 bg-severity-low/10 text-severity-low',
      },
    },
    defaultVariants: {
      tone: 'neutral',
    },
  },
)

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, severity, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone, severity }), className)} {...props} />
}
