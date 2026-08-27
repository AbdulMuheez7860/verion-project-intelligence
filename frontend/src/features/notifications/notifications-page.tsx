import { PageHeader } from '@/components/layout/page-header'
import { NotificationCenterPanel } from '@/components/notifications/notification-center'

export function NotificationsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Alerts"
        title="Notifications"
        description="Engineering events that need your attention."
      />
      <NotificationCenterPanel />
    </div>
  )
}
