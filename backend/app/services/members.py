from app.lib.dashboard_helpers import format_datetime
from app.repositories.invitations import InvitationRepository
from app.repositories.memberships import MembershipRepository
from app.repositories.users import UserRepository
from app.schemas.auth import MembershipRole
from app.schemas.invitations import InvitationCreateRequest, InvitationResponse
from app.schemas.members import MemberResponse, MemberRoleUpdateRequest
from app.schemas.pagination import PaginatedResponse
from app.services.audit_logs import AuditLogService
from app.services.notification_events import NotificationEventService


class MembersService:
    def __init__(
        self,
        memberships: MembershipRepository,
        users: UserRepository,
        invitations: InvitationRepository,
        audit: AuditLogService,
        notification_events: NotificationEventService | None = None,
    ) -> None:
        self._memberships = memberships
        self._users = users
        self._invitations = invitations
        self._audit = audit
        self._notification_events = notification_events

    async def list_members(
        self,
        organization_id: str,
        *,
        current_user_id: str,
        page: int,
        page_size: int,
        role: str | None = None,
        q: str | None = None,
    ) -> PaginatedResponse[MemberResponse]:
        docs, total = await self._memberships.list_by_organization(
            organization_id,
            skip=(page - 1) * page_size,
            limit=page_size,
            role=role,
        )
        items: list[MemberResponse] = []
        for doc in docs:
            user = await self._users.get_by_id(str(doc.get("user_id", "")))
            if not user:
                continue
            if q and q.lower() not in user.get("email", "").lower() and q.lower() not in user.get("name", "").lower():
                continue
            items.append(
                MemberResponse(
                    id=doc["id"],
                    user_id=user["id"],
                    name=user.get("name", ""),
                    email=user.get("email", ""),
                    role=MembershipRole(doc.get("role", "viewer")),
                    joined_at=format_datetime(doc.get("created_at")),
                    status="active",
                    is_current_user=user["id"] == current_user_id,
                ),
            )
        return PaginatedResponse.build(items, total=total, page=page, page_size=page_size)

    async def _ensure_not_last_admin(
        self,
        organization_id: str,
        membership: dict,
        *,
        new_role: MembershipRole | None = None,
    ) -> None:
        role = membership.get("role")
        if role not in {"admin", "owner"}:
            return
        if new_role in {MembershipRole.ADMIN, MembershipRole.OWNER}:
            return
        admin_count = await self._memberships.count_admins(organization_id)
        if admin_count <= 1:
            raise ValueError("Cannot remove or demote the last administrator.")

    async def update_member_role(
        self,
        organization_id: str,
        membership_id: str,
        payload: MemberRoleUpdateRequest,
        *,
        actor_user_id: str,
    ) -> MemberResponse | None:
        if payload.role == MembershipRole.OWNER:
            raise ValueError("Owner role cannot be assigned through settings.")
        membership = await self._memberships.get_by_id(membership_id)
        if not membership or membership.get("organization_id") != organization_id:
            return None
        await self._ensure_not_last_admin(organization_id, membership, new_role=payload.role)
        previous_role = membership.get("role")
        updated = await self._memberships.update_role(
            membership_id,
            organization_id,
            role=payload.role,
        )
        if not updated:
            return None
        user = await self._users.get_by_id(str(updated.get("user_id", "")))
        await self._audit.record(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="member.role_changed",
            resource_type="member",
            resource_id=membership_id,
            metadata={"previous_role": previous_role, "new_role": payload.role.value},
        )
        if self._notification_events and user:
            await self._notification_events.emit_workspace_event(
                organization_id=organization_id,
                notification_type="workspace.role_changed",
                title="Member role changed",
                body=f"{user.get('name', 'Member')} role changed from {previous_role} to {payload.role.value}.",
                href="/app/settings/members",
                idempotency_key=f"workspace.role_changed:{membership_id}:{payload.role.value}",
                resource_type="member",
                resource_id=membership_id,
            )
        return MemberResponse(
            id=updated["id"],
            user_id=user["id"] if user else "",
            name=user.get("name", "") if user else "",
            email=user.get("email", "") if user else "",
            role=payload.role,
            joined_at=format_datetime(updated.get("created_at")),
            is_current_user=user["id"] == actor_user_id if user else False,
        )

    async def remove_member(
        self,
        organization_id: str,
        membership_id: str,
        *,
        actor_user_id: str,
    ) -> bool:
        membership = await self._memberships.get_by_id(membership_id)
        if not membership or membership.get("organization_id") != organization_id:
            return False
        if membership.get("user_id") == actor_user_id:
            raise ValueError("You cannot remove yourself.")
        await self._ensure_not_last_admin(organization_id, membership)
        deleted = await self._memberships.delete_membership(membership_id, organization_id)
        if deleted:
            await self._audit.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="member.removed",
                resource_type="member",
                resource_id=membership_id,
            )
            if self._notification_events:
                await self._notification_events.emit_workspace_event(
                    organization_id=organization_id,
                    notification_type="workspace.member_removed",
                    title="Member removed",
                    body="A member was removed from this workspace.",
                    href="/app/settings/members",
                    idempotency_key=f"workspace.member_removed:{membership_id}",
                    resource_type="member",
                    resource_id=membership_id,
                )
        return deleted

    async def create_invitation(
        self,
        organization_id: str,
        payload: InvitationCreateRequest,
        *,
        actor_user_id: str,
    ) -> InvitationResponse:
        if payload.role == MembershipRole.OWNER:
            raise ValueError("Cannot invite with owner role.")
        email = str(payload.email).lower().strip()
        existing_user = await self._users.get_by_email(email)
        if existing_user:
            membership = await self._memberships.get_for_user_and_organization(
                user_id=existing_user["id"],
                organization_id=organization_id,
            )
            if membership:
                raise ValueError("User is already a member of this workspace.")
            if existing_user.get("organization_id") != organization_id:
                raise ValueError("User already belongs to another workspace.")
        pending = await self._invitations.get_pending_by_email(organization_id, email)
        if pending:
            raise ValueError("A pending invitation already exists for this email.")
        invitation = await self._invitations.create(
            organization_id=organization_id,
            email=email,
            role=payload.role,
            invited_by_user_id=actor_user_id,
        )
        await self._audit.record(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="member.invited",
            resource_type="invitation",
            resource_id=invitation["id"],
            metadata={"email": email, "role": payload.role.value},
        )
        if self._notification_events:
            await self._notification_events.emit_workspace_event(
                organization_id=organization_id,
                notification_type="workspace.member_invited",
                title="Member invited",
                body=f"Invitation sent to {email} as {payload.role.value}.",
                href="/app/settings/members",
                idempotency_key=f"workspace.member_invited:{invitation['id']}",
                resource_type="invitation",
                resource_id=invitation["id"],
            )
        return self._to_invitation(invitation)

    async def list_invitations(self, organization_id: str) -> list[InvitationResponse]:
        docs = await self._invitations.list_by_organization(organization_id)
        return [self._to_invitation(doc) for doc in docs]

    async def revoke_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        *,
        actor_user_id: str,
    ) -> InvitationResponse | None:
        revoked = await self._invitations.revoke(invitation_id, organization_id)
        if not revoked:
            return None
        await self._audit.record(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="invitation.revoked",
            resource_type="invitation",
            resource_id=invitation_id,
        )
        if self._notification_events:
            await self._notification_events.emit_workspace_event(
                organization_id=organization_id,
                notification_type="workspace.invitation_revoked",
                title="Invitation revoked",
                body="A pending workspace invitation was revoked.",
                href="/app/settings/members",
                idempotency_key=f"workspace.invitation_revoked:{invitation_id}",
                resource_type="invitation",
                resource_id=invitation_id,
            )
        return self._to_invitation(revoked)

    @staticmethod
    def _to_invitation(doc: dict) -> InvitationResponse:
        return InvitationResponse(
            id=doc["id"],
            email=doc.get("email", ""),
            role=MembershipRole(doc.get("role", "member")),
            status=str(doc.get("status", "pending")),
            created_at=format_datetime(doc.get("created_at")),
            expires_at=format_datetime(doc.get("expires_at")),
            email_delivery_configured=False,
        )
