from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

SENSITIVE_KEYS = frozenset({
    "password",
    "password_hash",
    "access_token",
    "access_token_encrypted",
    "refresh_token",
    "secret",
    "token",
})


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if any(sensitive in lowered for sensitive in SENSITIVE_KEYS):
            continue
        clean[key] = value
    return clean or None


class AuditLogRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["audit_logs"]

    async def create(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "actor_user_id": actor_user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": _sanitize_metadata(metadata),
            "created_at": now,
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_paginated(
        self,
        organization_id: str,
        *,
        skip: int,
        limit: int,
        action: str | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        q: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        sort: Literal["created_at", "action"] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if action:
            query["action"] = action
        if actor_id:
            query["actor_user_id"] = actor_id
        if resource_type:
            query["resource_type"] = resource_type
        if started_from or started_to:
            date_filter: dict[str, Any] = {}
            if started_from:
                date_filter["$gte"] = started_from
            if started_to:
                date_filter["$lte"] = started_to
            query["created_at"] = date_filter
        if q:
            query["$or"] = [
                {"action": {"$regex": q, "$options": "i"}},
                {"resource_type": {"$regex": q, "$options": "i"}},
                {"resource_id": {"$regex": q, "$options": "i"}},
            ]

        sort_dir = -1 if order == "desc" else 1
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort(sort, sort_dir).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total
