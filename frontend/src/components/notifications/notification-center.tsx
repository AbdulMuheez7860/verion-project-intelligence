import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { notificationsApi } from '@/api/notifications'
import { formatNotificationTime, NotificationSeverityBadge } from '@/components/notifications/notification-helpers'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { EmptyState } from '@/components/states/empty-state'
import { TablePagination } from '@/components/tables/table-pagination'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useNotifications, useUnreadNotificationCount } from '@/hooks/use-notifications'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import { ApiError } from '@/types/api'

export function NotificationCenterPanel() {
  const [page, setPage] = useState(1)
  const { data, status, reload } = useNotifications({ page, pageSize: 20 })
  const { refresh: refreshUnread } = useUnreadNotificationCount(0)
  const { push } = useToast()

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id)
      void reload()
      void refreshUnread()
    } catch (err) {
      push({
        title: 'Unable to mark notification read',
        description: err instanceof ApiError ? err.message : undefined,
        tone: 'error',
      })
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead()
      push({ title: 'All notifications marked read', tone: 'success' })
      void reload()
      void refreshUnread()
    } catch (err) {
      push({
        title: 'Unable to mark all read',
        description: err instanceof ApiError ? err.message : undefined,
        tone: 'error',
      })
    }
  }

  if (status === 'loading') return <LoadingState label="Loading notifications…" />
  if (status === 'error') return <ErrorState title="Unable to load notifications" onRetry={() => void reload()} />

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Notification center</CardTitle>
        {data && data.items.some((item) => !item.read) ? (
          <Button size="sm" variant="outline" onClick={() => void handleMarkAllRead()}>
            Mark all read
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {data && data.items.length > 0 ? (
          <>
            <ul className="space-y-2" aria-live="polite">
              {data.items.map((notification) => (
                <li
                  key={notification.id}
                  className={cn(
                    'rounded-lg border border-border p-4',
                    !notification.read && 'border-primary/30 bg-primary/5',
                  )}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <NotificationSeverityBadge severity={notification.severity} />
                        {!notification.read ? (
                          <span className="text-xs font-medium text-primary">Unread</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Read</span>
                        )}
                        <time className="text-xs text-muted-foreground" dateTime={notification.createdAt ?? undefined}>
                          {formatNotificationTime(notification.createdAt)}
                        </time>
                      </div>
                      <div>
                        <p className="font-medium">{notification.title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{notification.body}</p>
                        {notification.repositoryName ? (
                          <p className="mt-1 text-xs text-muted-foreground">Repository: {notification.repositoryName}</p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button asChild size="sm" variant="outline">
                          <Link to={notification.href}>View details</Link>
                        </Button>
                        {!notification.read ? (
                          <Button size="sm" variant="ghost" onClick={() => void handleMarkRead(notification.id)}>
                            Mark read
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            <TablePagination
              page={data.page}
              pageSize={data.pageSize}
              total={data.total}
              hasNext={data.hasNext}
              onPageChange={setPage}
              label="notifications"
            />
          </>
        ) : (
          <EmptyState
            title="No notifications yet"
            description="When Verion detects analysis results, security findings, regressions, or workspace events, they will appear here."
            icon={<Bell className="size-5" aria-hidden="true" />}
          />
        )}
      </CardContent>
    </Card>
  )
}
