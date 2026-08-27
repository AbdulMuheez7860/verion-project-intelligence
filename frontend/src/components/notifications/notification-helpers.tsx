import type { NotificationSeverity } from '@/types/api'
import { Badge } from '@/components/ui/badge'

const SEVERITY_LABEL: Record<NotificationSeverity, string> = {
  critical: 'Critical',
  high: 'High',
  warning: 'Warning',
  info: 'Info',
}

const SEVERITY_TONE: Record<NotificationSeverity, 'critical' | 'warning' | 'healthy' | 'neutral'> = {
  critical: 'critical',
  high: 'warning',
  warning: 'warning',
  info: 'neutral',
}

export function NotificationSeverityBadge({ severity }: { severity: NotificationSeverity }) {
  return (
    <Badge tone={SEVERITY_TONE[severity]}>
      {SEVERITY_LABEL[severity]}
    </Badge>
  )
}

export function formatNotificationTime(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleString()
}
