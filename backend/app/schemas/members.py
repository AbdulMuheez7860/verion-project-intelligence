from app.schemas.auth import MembershipRole
from app.schemas.common import APIModel


class MemberResponse(APIModel):
    id: str
    user_id: str
    name: str
    email: str
    role: MembershipRole
    joined_at: str | None = None
    status: str = "active"
    is_current_user: bool = False


class MemberRoleUpdateRequest(APIModel):
    role: MembershipRole
