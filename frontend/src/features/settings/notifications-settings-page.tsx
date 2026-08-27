import { useEffect, useState } from 'react'
import { notificationsApi } from '@/api/notifications'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { ApiError, type NotificationPreferences } from '@/types/api'

const PREFERENCE_ITEMS: { key: keyof NotificationPreferences; label: string; description: string }[] = [
  { key: 'securityAlerts', label: 'Security alerts', description: 'Critical security findings detected in your repositories.' },
  { key: 'dependencyAlerts', label: 'Dependency alerts', description: 'Critical dependency vulnerabilities.' },
  { key: 'prRiskAlerts', label: 'PR risk alerts', description: 'High-risk pull requests that may need review.' },
  { key: 'analysisAlerts', label: 'Analysis alerts', description: 'Analysis completed, failed, or stale repositories.' },
  { key: 'regressionAlerts', label: 'Regression alerts', description: 'Health or quality regressions detected over time.' },
  { key: 'workspaceAlerts', label: 'Workspace alerts', description: 'Member, invitation, and integration events (admins).' },
]

export function NotificationsSettingsPage() {
  const { push } = useToast()
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    notificationsApi
      .preferences()
      .then((data) => {
        setPrefs(data)
        setStatus('success')
      })
      .catch(() => setStatus('error'))
  }, [])

  const save = async () => {
    if (!prefs) return
    setSaving(true)
    try {
      const updated = await notificationsApi.updatePreferences(prefs)
      setPrefs(updated)
      push({ title: 'Notification preferences updated', tone: 'success' })
    } catch (err) {
      push({
        title: 'Unable to update preferences',
        description: err instanceof ApiError ? err.message : undefined,
        tone: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  if (status === 'loading') return <LoadingState label="Loading notification preferences…" />
  if (status === 'error' || !prefs) return <ErrorState title="Unable to load notification preferences" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
        <CardDescription>
          Control which in-app notifications you receive. Email delivery is not configured.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {PREFERENCE_ITEMS.map((item) => (
          <div key={item.key} className="flex items-start justify-between gap-4 rounded-lg border border-border p-4">
            <div>
              <Label htmlFor={item.key} className="text-sm font-medium">{item.label}</Label>
              <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
            </div>
            <input
              id={item.key}
              type="checkbox"
              className="mt-1 size-4 rounded border-input"
              checked={prefs[item.key]}
              onChange={(event) => setPrefs((current) => current ? { ...current, [item.key]: event.target.checked } : current)}
              aria-describedby={`${item.key}-description`}
            />
          </div>
        ))}
        <Button onClick={() => void save()} disabled={saving}>
          Save preferences
        </Button>
      </CardContent>
    </Card>
  )
}
