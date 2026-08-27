import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { notificationsApi } from '@/api/notifications'
import { formatNotificationTime, NotificationSeverityBadge } from '@/components/notifications/notification-helpers'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useUnreadNotificationCount } from '@/hooks/use-notifications'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import { ApiError, type Notification } from '@/types/api'

export function NotificationDropdown() {
  const { count, refresh } = useUnreadNotificationCount()
  const { push } = useToast()
  const [items, setItems] = useState<Notification[]>([])
  const [loading, setLoading] = useState(false)

  const loadPreview = async () => {
    setLoading(true)
    try {
      const result = await notificationsApi.list({ page: 1, pageSize: 5 })
      setItems(result.items)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPreview()
  }, [count])

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id)
      void refresh()
      void loadPreview()
    } catch (err) {
      push({
        title: 'Unable to mark notification read',
        description: err instanceof ApiError ? err.message : undefined,
        tone: 'error',
      })
    }
  }

  return (
    <DropdownMenu onOpenChange={(open) => open && void loadPreview()}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={`Notifications${count > 0 ? `, ${count} unread` : ''}`}
        >
          <span className="sr-only" aria-live="polite">
            {count > 0 ? `${count} unread notifications` : 'No unread notifications'}
          </span>
          <Bell className="size-4" aria-hidden="true" />
          {count > 0 ? (
            <span className="absolute right-1 top-1 grid min-w-4 place-items-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
              {count > 9 ? '9+' : count}
            </span>
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {loading ? (
          <p className="px-3 py-4 text-sm text-muted-foreground">Loading…</p>
        ) : items.length === 0 ? (
          <p className="px-3 py-4 text-sm text-muted-foreground">No notifications yet.</p>
        ) : (
          <div className="max-h-80 overflow-y-auto">
            {items.map((notification) => (
              <div key={notification.id} className="border-b border-border px-3 py-3 last:border-0">
                <div className="flex items-center justify-between gap-2">
                  <NotificationSeverityBadge severity={notification.severity} />
                  <time className="text-[11px] text-muted-foreground">{formatNotificationTime(notification.createdAt)}</time>
                </div>
                <p className={cn('mt-1 text-sm font-medium', !notification.read && 'text-foreground')}>{notification.title}</p>
                <p className="line-clamp-2 text-xs text-muted-foreground">{notification.body}</p>
                <div className="mt-2 flex gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link to={notification.href}>Open</Link>
                  </Button>
                  {!notification.read ? (
                    <Button size="sm" variant="ghost" onClick={() => void handleMarkRead(notification.id)}>
                      Mark read
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
        <DropdownMenuSeparator />
        <div className="p-2">
          <Button asChild variant="ghost" size="sm" className="w-full justify-start">
            <Link to="/app/notifications">View all</Link>
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
