from app.core.config import get_settings
from app.lib.dashboard_helpers import format_datetime
from app.repositories.memberships import MembershipRepository
from app.repositories.repositories import RepositoryRepository
from app.repositories.users import OrganizationRepository
from app.schemas.organization_settings import OrganizationOverviewResponse, OrganizationUpdateRequest


from app.services.audit_logs import AuditLogService


class OrganizationSettingsService:
    def __init__(
        self,
        organizations: OrganizationRepository,
        memberships: MembershipRepository,
        repositories: RepositoryRepository,
        audit: AuditLogService | None = None,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._repositories = repositories
        self._audit = audit

    async def get_overview(self, organization_id: str, *, role: str) -> OrganizationOverviewResponse | None:
        org = await self._organizations.get_by_id(organization_id)
        if not org:
            return None
        repo_count = await self._repositories.count_by_organization(organization_id)
        member_count = await self._memberships.count_by_organization(organization_id)
        return OrganizationOverviewResponse(
            id=org["id"],
            name=org.get("name", ""),
            slug=org.get("slug", ""),
            created_at=format_datetime(org.get("created_at")),
            current_user_role=role,
            repository_count=repo_count,
            member_count=member_count,
        )

    async def update_organization(
        self,
        organization_id: str,
        payload: OrganizationUpdateRequest,
        *,
        actor_user_id: str | None = None,
    ) -> OrganizationOverviewResponse | None:
        name = payload.name.strip()
        if not name:
            raise ValueError("Organization name is required.")
        org = await self._organizations.get_by_id(organization_id)
        if not org:
            return None
        updated = await self._organizations.update_name(organization_id, name=name)
        if not updated:
            return None
        if self._audit and actor_user_id:
            await self._audit.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="organization.updated",
                resource_type="organization",
                resource_id=organization_id,
                metadata={"previous_name": org.get("name"), "new_name": name},
            )
        return await self.get_overview(organization_id, role="admin")
