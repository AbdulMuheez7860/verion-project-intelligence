import { useState } from 'react'
import { authService } from '@/api/authService'
import { useAuth } from '@/hooks/use-auth'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError } from '@/types/api'

export function AccountSettingsPage() {
  const { user, refresh } = useAuth()
  const { push } = useToast()
  const [name, setName] = useState(user?.name ?? '')
  const [timezone, setTimezone] = useState(user?.timezone ?? 'UTC')

  const saveProfile = async () => {
    try {
      await authService.updateProfile({ name, timezone })
      await refresh()
      push({ title: 'Profile updated', tone: 'success' })
    } catch (err) {
      push({ title: 'Unable to update profile', description: err instanceof ApiError ? err.message : undefined, tone: 'error' })
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Account</CardTitle></CardHeader>
      <CardContent className="grid max-w-xl gap-4 text-sm">
        <div className="grid gap-2">
          <Label htmlFor="account-name">Name</Label>
          <Input id="account-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="account-email">Email</Label>
          <Input id="account-email" value={user?.email ?? ''} readOnly aria-describedby="email-hint" />
          <p id="email-hint" className="text-xs text-muted-foreground">Email cannot be changed in this workspace.</p>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="account-timezone">Timezone</Label>
          <Input id="account-timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
        </div>
        <Button size="sm" className="w-fit" onClick={() => void saveProfile()}>Save profile</Button>
      </CardContent>
    </Card>
  )
}

export function SecuritySettingsPage() {
  const { logout } = useAuth()
  const { push } = useToast()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')

  const changePassword = async () => {
    try {
      await authService.changePassword({ currentPassword, newPassword })
      setCurrentPassword('')
      setNewPassword('')
      push({ title: 'Password changed', tone: 'success' })
    } catch (err) {
      push({ title: 'Unable to change password', description: err instanceof ApiError ? err.message : undefined, tone: 'error' })
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Session</CardTitle></CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">You are signed in with an active session.</p>
          <Button size="sm" variant="outline" className="mt-3" onClick={() => void logout()}>Sign out</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Password</CardTitle></CardHeader>
        <CardContent className="grid max-w-md gap-3 text-sm">
          <div className="grid gap-2">
            <Label htmlFor="current-password">Current password</Label>
            <Input id="current-password" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="new-password">New password</Label>
            <Input id="new-password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          </div>
          <Button size="sm" className="w-fit" onClick={() => void changePassword()}>Change password</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Multi-factor authentication</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">Not available yet.</CardContent>
      </Card>
    </div>
  )
}
