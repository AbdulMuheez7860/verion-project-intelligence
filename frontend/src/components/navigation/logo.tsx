import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

export function Logo({
  compact = false,
  variant = 'default',
  className,
}: {
  compact?: boolean
  variant?: 'default' | 'inverse'
  className?: string
}) {
  const textClass = variant === 'inverse' ? 'text-primary-foreground' : 'text-foreground'
  const markClass = variant === 'inverse' ? 'border-primary-foreground/20 bg-primary' : 'border-border bg-card'

  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <div
        className={cn(
          'grid size-8 place-items-center rounded-md border shadow-elevation-1',
          markClass,
        )}
        aria-hidden="true"
      >
        <svg viewBox="0 0 32 32" className="size-5" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M8 9.5L16 23.5L24 9.5"
            stroke={variant === 'inverse' ? '#F4F7FC' : 'currentColor'}
            strokeWidth="2.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={variant === 'inverse' ? undefined : 'text-primary'}
          />
          <path
            d="M11.5 9.5H20.5"
            stroke={variant === 'inverse' ? '#7B9AD4' : 'currentColor'}
            strokeWidth="2"
            strokeLinecap="round"
            className={variant === 'inverse' ? undefined : 'text-muted-foreground'}
          />
        </svg>
      </div>
      {!compact ? (
        <div className="min-w-0">
          <span className={cn('block text-sm font-semibold tracking-[0.14em]', textClass)}>VERION</span>
          <span className={cn('block text-[10px] font-medium uppercase tracking-[0.12em] opacity-70', textClass)}>
            Engineering intelligence
          </span>
        </div>
      ) : null}
    </div>
  )
}

export function LogoLink({
  to = '/app/dashboard',
  compact = false,
  variant = 'default',
  onClick,
}: {
  to?: string
  compact?: boolean
  variant?: 'default' | 'inverse'
  onClick?: () => void
}) {
  return (
    <Link to={to} onClick={onClick} className="inline-flex rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <Logo compact={compact} variant={variant} />
    </Link>
  )
}
