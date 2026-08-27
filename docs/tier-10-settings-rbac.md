# Tier 10 — Settings, RBAC & Workspace Administration

## Architecture

- Central permissions in `app/core/permissions.py` (backend) and `use-permissions.ts` (frontend)
- Organization APIs under `/api/v1/organization`
- Audit logs at `/api/v1/audit-logs` (admin only)
- Profile/password at `/api/v1/auth/me` and `/api/v1/auth/change-password`

## Collections

- `invitations` — pending workspace invites (email delivery not configured)
- `audit_logs` — organization-scoped admin activity

## RBAC

| Permission | Viewer | Member | Admin/Owner |
|------------|--------|--------|-------------|
| settings.read | ✓ | ✓ | ✓ |
| settings.update | | | ✓ |
| members.read | ✓ | ✓ | ✓ |
| members.invite/update/remove | | | ✓ |
| audit.read | | | ✓ |
| integrations.manage | | | ✓ |

## Frontend routes

- `/app/settings/general`
- `/app/settings/members`
- `/app/settings/integrations`
- `/app/settings/analysis`
- `/app/settings/security`
- `/app/settings/audit-log`
- `/app/settings/account`

## Known limitations

- No email delivery for invitations
- No MFA
- No multi-workspace switching
- Slug is immutable when renaming organization
- Single-org user model limits cross-workspace invites
