from typing import Literal

from app.schemas.common import APIModel

AuditSortField = Literal["created_at", "action"]


class AuditLogResponse(APIModel):
    id: str
    action: str
    actor_user_id: str
    actor_name: str
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict[str, object] | None = None
    created_at: str | None = None
