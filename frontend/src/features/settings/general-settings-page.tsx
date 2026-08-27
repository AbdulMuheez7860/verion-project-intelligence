import { useCallback, useEffect, useState } from 'react'
import { organizationApi } from '@/api/organization'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePermissions } from '@/hooks/use-permissions'
import { useToast } from '@/hooks/use-toast'
import { ApiError } from '@/types/api'
import type { OrganizationOverview } from '@/types/api'

export function GeneralSettingsPage() {
  const { can } = usePermissions()
  const { push } = useToast()
  const [data, setData] = useState<OrganizationOverview | null>(null)
  const [name, setName] = useState('')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setStatus('loading')
    try {
      const overview = await organizationApi.overview()
      setData(overview)
      setName(overview.name)
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleSave = async () => {
    if (!can('settings.update')) return
    setSaving(true)
    try {
      const updated = await organizationApi.update({ name })
      setData(updated)
      push({ title: 'Organization settings updated', tone: 'success' })
    } catch (err) {
      const message = err instanceof ApiError ? `${err.message}${err.requestId ? ` Request ID: ${err.requestId}` : ''}` : 'Unable to update settings.'
      push({ title: 'Unable to update settings', description: message, tone: 'error' })
    } finally {
      setSaving(false)
    }
  }

  if (status === 'loading') return <LoadingState label="Loading workspace settings…" />
  if (status === 'error' || !data) return <ErrorState title="Unable to load settings" onRetry={() => void load()} />

  return (
    <Card>
      <CardHeader>
        <CardTitle>General</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div><dt className="text-muted-foreground">Workspace ID</dt><dd className="font-mono text-xs">{data.id}</dd></div>
          <div><dt className="text-muted-foreground">Slug</dt><dd>{data.slug}</dd></div>
          <div><dt className="text-muted-foreground">Created</dt><dd>{data.createdAt ? new Date(data.createdAt).toLocaleDateString() : '—'}</dd></div>
          <div><dt className="text-muted-foreground">Your role</dt><dd className="capitalize">{data.currentUserRole}</dd></div>
          <div><dt className="text-muted-foreground">Repositories</dt><dd>{data.repositoryCount}</dd></div>
          <div><dt className="text-muted-foreground">Members</dt><dd>{data.memberCount}</dd></div>
        </dl>
        {can('settings.update') ? (
          <div className="grid max-w-md gap-2 pt-2">
            <Label htmlFor="org-name">Organization name</Label>
            <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} aria-describedby="org-name-hint" />
            <p id="org-name-hint" className="text-xs text-muted-foreground">Changing the name does not change the workspace slug.</p>
            <div className="flex gap-2 pt-2">
              <Button size="sm" disabled={saving} onClick={() => void handleSave()}>Save</Button>
              <Button size="sm" variant="outline" onClick={() => setName(data.name)}>Cancel</Button>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
