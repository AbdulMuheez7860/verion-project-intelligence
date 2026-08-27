from app.schemas.common import APIModel


class OrganizationOverviewResponse(APIModel):
    id: str
    name: str
    slug: str
    created_at: str | None = None
    current_user_role: str
    repository_count: int = 0
    member_count: int = 0


class OrganizationUpdateRequest(APIModel):
    name: str
