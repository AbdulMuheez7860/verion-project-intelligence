# Tier 10 — Settings, RBAC & Workspace Administration

## Reuse
- `MembershipRole`, `MembershipContext`, `RequireAdmin/Viewer/Member`
- GitHub integration at `/integrations/github`
- Cookie session auth, single org per user
- Toast/dialog patterns from Tier 9

## New collections
- `invitations` — pending workspace invites
- `audit_logs` — admin-visible activity history

## API surface
- `GET/PATCH /organization` — workspace general settings
- `GET/PATCH/DELETE /organization/members/{id}`
- `POST/GET/DELETE /organization/invitations`
- `GET /audit-logs` — admin only
- `PATCH /auth/me`, `POST /auth/change-password`
- `GET /settings/analysis` — read-only scanner support

## RBAC
Central `permissions.py` with `can(role, permission)`; backend enforces on every mutation.

## Signup
Optional invitation token joins existing org instead of creating a new workspace.
