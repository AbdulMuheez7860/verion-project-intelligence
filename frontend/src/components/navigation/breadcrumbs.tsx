import { Link, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { getNavItemForPath } from '@/components/navigation/nav-config'
import { cn } from '@/lib/utils'

function formatSegment(segment: string): string {
  return segment
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function Breadcrumbs({ className }: { className?: string }) {
  const location = useLocation()
  const navItem = getNavItemForPath(location.pathname)
  const segments = location.pathname.split('/').filter(Boolean)

  if (segments[0] !== 'app') return null

  const crumbs: Array<{ label: string; to?: string }> = [{ label: 'App', to: '/app/dashboard' }]

  if (navItem) {
    crumbs.push({ label: navItem.label, to: navItem.to })
  } else if (segments.length > 1) {
    crumbs.push({ label: formatSegment(segments[1] ?? ''), to: `/app/${segments[1]}` })
  }

  if (segments.length > 2 && !navItem) {
    crumbs.push({ label: formatSegment(segments[segments.length - 1] ?? '') })
  }

  return (
    <nav aria-label="Breadcrumb" className={cn('hidden min-w-0 items-center gap-1 text-metadata md:flex', className)}>
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1
        return (
          <span key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-1">
            {index > 0 ? <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/70" aria-hidden="true" /> : null}
            {crumb.to && !isLast ? (
              <Link to={crumb.to} className="truncate hover:text-foreground">
                {crumb.label}
              </Link>
            ) : (
              <span className={cn('truncate', isLast && 'font-medium text-foreground')}>{crumb.label}</span>
            )}
          </span>
        )
      })}
    </nav>
  )
}
