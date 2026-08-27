from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_log_service, require_permission
from app.core.authorization import MembershipContext
from app.schemas.audit_logs import AuditLogResponse
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.audit_logs import AuditLogService

router = APIRouter(tags=["audit-logs"])


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    context: Annotated[MembershipContext, Depends(require_permission("audit.read"))],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[AuditLogService, Depends(get_audit_log_service)],
    q: str | None = None,
    action: str | None = None,
    actor_id: Annotated[str | None, Query(alias="actorId")] = None,
    resource_type: Annotated[str | None, Query(alias="resourceType")] = None,
    started_from: Annotated[str | None, Query(alias="from")] = None,
    started_to: Annotated[str | None, Query(alias="to")] = None,
    sort: Literal["created_at", "action"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> PaginatedResponse[AuditLogResponse]:
    return await service.list_logs(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        action=action,
        actor_id=actor_id,
        resource_type=resource_type,
        q=q,
        started_from=started_from,
        started_to=started_to,
        sort=sort,
        order=order,
    )
