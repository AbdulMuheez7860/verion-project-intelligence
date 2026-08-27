from typing import Any

from app.lib.dashboard_helpers import format_datetime
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.users import UserRepository


class AuditLogService:
    def __init__(self, audit_logs: AuditLogRepository, users: UserRepository) -> None:
        self._audit_logs = audit_logs
        self._users = users

    async def record(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._audit_logs.create(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )

    async def list_logs(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        action: str | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        q: str | None = None,
        started_from: str | None = None,
        started_to: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ):
        from datetime import datetime, UTC

        from app.schemas.audit_logs import AuditLogResponse
        from app.schemas.pagination import PaginatedResponse

        def parse_dt(value: str | None):
            if not value:
                return None
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                return None

        skip = (page - 1) * page_size
        docs, total = await self._audit_logs.list_paginated(
            organization_id,
            skip=skip,
            limit=page_size,
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            q=q,
            started_from=parse_dt(started_from),
            started_to=parse_dt(started_to),
            sort=sort if sort in {"created_at", "action"} else "created_at",
            order=order if order in {"asc", "desc"} else "desc",
        )
        actor_ids = {doc.get("actor_user_id") for doc in docs if doc.get("actor_user_id")}
        actor_names: dict[str, str] = {}
        for actor_id in actor_ids:
            if not isinstance(actor_id, str):
                continue
            user = await self._users.get_by_id(actor_id)
            if user:
                actor_names[actor_id] = user.get("name", "User")

        items = [
            AuditLogResponse(
                id=doc["id"],
                action=str(doc.get("action", "")),
                actor_user_id=str(doc.get("actor_user_id", "")),
                actor_name=actor_names.get(str(doc.get("actor_user_id", "")), "User"),
                resource_type=doc.get("resource_type"),
                resource_id=doc.get("resource_id"),
                metadata=doc.get("metadata"),
                created_at=format_datetime(doc.get("created_at")),
            )
            for doc in docs
        ]
        return PaginatedResponse.build(items, total=total, page=page, page_size=page_size)
