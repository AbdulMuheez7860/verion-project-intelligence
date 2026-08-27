import { useCallback, useEffect, useState } from 'react'
import { organizationApi } from '@/api/organization'
import { ErrorState } from '@/components/states/error-state'
import { LoadingState } from '@/components/states/loading-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePermissions } from '@/hooks/use-permissions'
import { useToast } from '@/hooks/use-toast'
import { ApiError } from '@/types/api'
import type { Invitation, Member, MembershipRole } from '@/types/api'

export function MembersSettingsPage() {
  const { can } = usePermissions()
  const { push } = useToast()
  const [members, setMembers] = useState<Member[]>([])
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<MembershipRole>('member')
  const [showInvite, setShowInvite] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<Member | null>(null)
  const [removing, setRemoving] = useState(false)

  const load = useCallback(async () => {
    setStatus('loading')
    try {
      const [memberPage, inviteList] = await Promise.all([
        organizationApi.members({ pageSize: 50 }),
        organizationApi.invitations(),
      ])
      setMembers(memberPage.items)
      setInvitations(inviteList)
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleInvite = async () => {
    try {
      await organizationApi.createInvitation({ email: inviteEmail, role: inviteRole })
      push({
        title: 'Invitation created',
        description: 'Email delivery is not configured.',
        tone: 'success',
      })
      setInviteEmail('')
      setShowInvite(false)
      void load()
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Unable to create invitation.'
      push({ title: 'Unable to create invitation', description: message, tone: 'error' })
    }
  }

  const handleRoleChange = async (member: Member, role: MembershipRole) => {
    try {
      await organizationApi.updateMemberRole(member.id, role)
      push({ title: 'Member role updated', tone: 'success' })
      void load()
    } catch (err) {
      push({ title: 'Unable to update role', description: err instanceof ApiError ? err.message : undefined, tone: 'error' })
    }
  }

  const handleRemove = async () => {
    if (!removeTarget) return
    setRemoving(true)
    try {
      await organizationApi.removeMember(removeTarget.id)
      push({ title: 'Member removed', tone: 'success' })
      setRemoveTarget(null)
      void load()
    } catch (err) {
      push({
        title: 'Unable to remove member',
        description: err instanceof ApiError ? err.message : undefined,
        tone: 'error',
      })
    } finally {
      setRemoving(false)
    }
  }

  if (status === 'loading') return <LoadingState label="Loading members…" />
  if (status === 'error') return <ErrorState title="Unable to load members" onRetry={() => void load()} />

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>Members & Access</CardTitle>
          {can('members.invite') ? (
            <Button size="sm" onClick={() => setShowInvite((v) => !v)}>Invite member</Button>
          ) : null}
        </CardHeader>
        <CardContent className="space-y-4">
          {showInvite ? (
            <div className="grid gap-3 rounded-md border border-border p-4 sm:grid-cols-[1fr_10rem_auto]">
              <div className="grid gap-1.5">
                <Label htmlFor="invite-email">Email</Label>
                <Input id="invite-email" type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="invite-role">Role</Label>
                <select id="invite-role" className="h-9 rounded-md border border-input bg-background px-3 text-sm" value={inviteRole} onChange={(e) => setInviteRole(e.target.value as MembershipRole)}>
                  <option value="viewer">Viewer</option>
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex items-end gap-2">
                <Button size="sm" onClick={() => void handleInvite()}>Send invitation</Button>
                <Button size="sm" variant="outline" onClick={() => setShowInvite(false)}>Cancel</Button>
              </div>
            </div>
          ) : null}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-muted-foreground">
                  <th className="px-2 py-2 font-medium">Member</th>
                  <th className="px-2 py-2 font-medium">Role</th>
                  <th className="px-2 py-2 font-medium">Joined</th>
                  <th className="px-2 py-2 font-medium">Status</th>
                  <th className="px-2 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-b border-border last:border-0">
                    <td className="px-2 py-3">
                      <p className="font-medium">{member.name}{member.isCurrentUser ? ' (you)' : ''}</p>
                      <p className="text-xs text-muted-foreground">{member.email}</p>
                    </td>
                    <td className="px-2 py-3 capitalize">{member.role}</td>
                    <td className="px-2 py-3 text-muted-foreground">{member.joinedAt ? new Date(member.joinedAt).toLocaleDateString() : '—'}</td>
                    <td className="px-2 py-3"><Badge tone="healthy">{member.status}</Badge></td>
                    <td className="px-2 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        {can('members.update_role') && !member.isCurrentUser && member.role !== 'owner' ? (
                          <select
                            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                            value={member.role}
                            onChange={(e) => void handleRoleChange(member, e.target.value as MembershipRole)}
                            aria-label={`Change role for ${member.name}`}
                          >
                            <option value="viewer">Viewer</option>
                            <option value="member">Member</option>
                            <option value="admin">Admin</option>
                          </select>
                        ) : null}
                        {can('members.remove') && !member.isCurrentUser && member.role !== 'owner' ? (
                          <Button size="sm" variant="outline" onClick={() => setRemoveTarget(member)}>
                            Remove
                          </Button>
                        ) : null}
                        {!can('members.update_role') && !can('members.remove') ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      {invitations.length > 0 ? (
        <Card>
          <CardHeader><CardTitle>Pending invitations</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {invitations.filter((i) => i.status === 'pending').map((invite) => (
              <div key={invite.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2 last:border-0">
                <span>{invite.email} · {invite.role}</span>
                {can('members.invite') ? (
                  <Button size="sm" variant="outline" onClick={() => void organizationApi.revokeInvitation(invite.id).then(() => load())}>Revoke</Button>
                ) : null}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
      <Dialog open={removeTarget !== null} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <DialogContent>
          <DialogTitle>Remove member</DialogTitle>
          <DialogDescription>
            Remove {removeTarget?.name} from this workspace? They will lose access immediately.
          </DialogDescription>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setRemoveTarget(null)} disabled={removing}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={() => void handleRemove()} disabled={removing}>
              Remove member
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
