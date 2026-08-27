from typing import Any

from app.lib.dashboard_helpers import format_datetime
from app.repositories.notification_preferences import NotificationPreferencesRepository
from app.repositories.notifications import NotificationRepository
from app.schemas.notifications import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationSeverity,
    NotificationType,
)
from app.schemas.pagination import PaginatedResponse


class NotificationService:
    def __init__(
        self,
        notifications: NotificationRepository,
        preferences: NotificationPreferencesRepository,
    ) -> None:
        self._notifications = notifications
        self._preferences = preferences

    def _to_response(self, doc: dict[str, Any]) -> NotificationResponse:
        return NotificationResponse(
            id=doc["id"],
            type=doc["type"],
            severity=doc["severity"],
            title=doc["title"],
            body=doc["body"],
            href=doc["href"],
            repository_id=doc.get("repository_id"),
            repository_name=doc.get("repository_name"),
            resource_type=doc.get("resource_type"),
            resource_id=doc.get("resource_id"),
            read=doc.get("read_at") is not None,
            created_at=format_datetime(doc.get("created_at")),
        )

    async def list_notifications(
        self,
        *,
        organization_id: str,
        user_id: str,
        page: int,
        page_size: int,
        unread_only: bool = False,
        notification_type: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> PaginatedResponse[NotificationResponse]:
        skip = (page - 1) * page_size
        docs, total = await self._notifications.list_for_user(
            organization_id=organization_id,
            user_id=user_id,
            skip=skip,
            limit=page_size,
            unread_only=unread_only,
            notification_type=notification_type,
            sort=sort if sort in {"created_at", "severity"} else "created_at",
            order=order if order in {"asc", "desc"} else "desc",
        )
        items = [self._to_response(doc) for doc in docs]
        return PaginatedResponse.build(items, total=total, page=page, page_size=page_size)

    async def unread_count(self, *, organization_id: str, user_id: str) -> int:
        return await self._notifications.count_unread(
            organization_id=organization_id,
            user_id=user_id,
        )

    async def mark_read(
        self,
        notification_id: str,
        *,
        organization_id: str,
        user_id: str,
    ) -> NotificationResponse | None:
        doc = await self._notifications.mark_read(
            notification_id=notification_id,
            organization_id=organization_id,
            user_id=user_id,
        )
        if not doc:
            return None
        return self._to_response(doc)

    async def mark_all_read(self, *, organization_id: str, user_id: str) -> int:
        return await self._notifications.mark_all_read(
            organization_id=organization_id,
            user_id=user_id,
        )

    async def get_preferences(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> NotificationPreferencesResponse:
        doc = await self._preferences.get_or_create(
            organization_id=organization_id,
            user_id=user_id,
        )
        return NotificationPreferencesResponse(
            security_alerts=bool(doc.get("security_alerts", True)),
            dependency_alerts=bool(doc.get("dependency_alerts", True)),
            analysis_alerts=bool(doc.get("analysis_alerts", True)),
            pr_risk_alerts=bool(doc.get("pr_risk_alerts", True)),
            regression_alerts=bool(doc.get("regression_alerts", True)),
            workspace_alerts=bool(doc.get("workspace_alerts", True)),
        )

    async def update_preferences(
        self,
        *,
        organization_id: str,
        user_id: str,
        payload: NotificationPreferencesUpdate,
    ) -> NotificationPreferencesResponse:
        updates: dict[str, bool] = {}
        if payload.security_alerts is not None:
            updates["security_alerts"] = payload.security_alerts
        if payload.dependency_alerts is not None:
            updates["dependency_alerts"] = payload.dependency_alerts
        if payload.pr_risk_alerts is not None:
            updates["pr_risk_alerts"] = payload.pr_risk_alerts
        if payload.analysis_alerts is not None:
            updates["analysis_alerts"] = payload.analysis_alerts
        if payload.regression_alerts is not None:
            updates["regression_alerts"] = payload.regression_alerts
        if payload.workspace_alerts is not None:
            updates["workspace_alerts"] = payload.workspace_alerts
        if not updates:
            return await self.get_preferences(organization_id=organization_id, user_id=user_id)
        doc = await self._preferences.update(
            organization_id=organization_id,
            user_id=user_id,
            updates=updates,
        )
        return NotificationPreferencesResponse(
            security_alerts=bool(doc.get("security_alerts", True)),
            dependency_alerts=bool(doc.get("dependency_alerts", True)),
            analysis_alerts=bool(doc.get("analysis_alerts", True)),
            pr_risk_alerts=bool(doc.get("pr_risk_alerts", True)),
            regression_alerts=bool(doc.get("regression_alerts", True)),
            workspace_alerts=bool(doc.get("workspace_alerts", True)),
        )

    async def create_notification(
        self,
        *,
        organization_id: str,
        user_id: str,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        body: str,
        href: str,
        idempotency_key: str,
        repository_id: str | None = None,
        repository_name: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return await self._notifications.create(
            organization_id=organization_id,
            user_id=user_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            body=body,
            href=href,
            idempotency_key=idempotency_key,
            repository_id=repository_id,
            repository_name=repository_name,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )
