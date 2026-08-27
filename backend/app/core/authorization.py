from app.schemas.auth import MembershipRole

ROLE_RANK: dict[MembershipRole, int] = {
    MembershipRole.VIEWER: 1,
    MembershipRole.MEMBER: 2,
    MembershipRole.ADMIN: 3,
    MembershipRole.OWNER: 4,
}


class MembershipContext:
    def __init__(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: MembershipRole,
        membership_id: str,
    ) -> None:
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role
        self.membership_id = membership_id

    def has_min_role(self, minimum: MembershipRole) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[minimum]
