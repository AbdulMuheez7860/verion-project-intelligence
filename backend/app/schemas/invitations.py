from app.schemas.auth import MembershipRole
from app.schemas.common import APIModel


class InvitationCreateRequest(APIModel):
    email: str
    role: MembershipRole = MembershipRole.MEMBER


class InvitationResponse(APIModel):
    id: str
    email: str
    role: MembershipRole
    status: str
    created_at: str | None = None
    expires_at: str | None = None
    email_delivery_configured: bool = False
