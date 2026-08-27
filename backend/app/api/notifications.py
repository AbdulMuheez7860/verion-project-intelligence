from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_notification_service, require_permission
from app.core.authorization import MembershipContext
from app.schemas.notifications import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    UnreadCountResponse,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.notifications import NotificationService

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    context: Annotated[MembershipContext, Depends(require_permission("notifications.read"))],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    unread_only: Annotated[bool, Query(alias="unreadOnly")] = False,
    notification_type: Annotated[str | None, Query(alias="type")] = None,
    sort: Literal["created_at", "severity"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> PaginatedResponse[NotificationResponse]:
    return await service.list_notifications(
        organization_id=context.organization_id,
        user_id=context.user_id,
        page=pagination.page,
        page_size=pagination.page_size,
        unread_only=unread_only,
        notification_type=notification_type,
        sort=sort,
        order=order,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    context: Annotated[MembershipContext, Depends(require_permission("notifications.read"))],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UnreadCountResponse:
    count = await service.unread_count(
        organization_id=context.organization_id,
        user_id=context.user_id,
    )
    return UnreadCountResponse(count=count)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    context: Annotated[MembershipContext, Depends(require_permission("notifications.read"))],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    result = await service.mark_read(
        notification_id,
        organization_id=context.organization_id,
        user_id=context.user_id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return result


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    context: Annotated[MembershipContext, Depends(require_permission("notifications.read"))],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> dict[str, int]:
    updated = await service.mark_all_read(
        organization_id=context.organization_id,
        user_id=context.user_id,
    )
    return {"updated": updated}


@router.get("/notification-preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    context: Annotated[MembershipContext, Depends(require_permission("notifications.preferences.update"))],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationPreferencesResponse:
    return await service.get_preferences(
        organization_id=context.organization_id,
        user_id=context.user_id,
    )


@router.put("/notification-preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    context: Annotated[MembershipContext, Depends(require_permission("notifications.preferences.update"))],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationPreferencesResponse:
    return await service.update_preferences(
        organization_id=context.organization_id,
        user_id=context.user_id,
        payload=payload,
    )
