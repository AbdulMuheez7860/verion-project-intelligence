from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class IntegrationEventRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["integration_events"]

    async def create(
        self,
        *,
        organization_id: str,
        event_type: str,
        status: str,
        message: str,
        repository_id: str | None = None,
        repository_name: str | None = None,
        delivery_id: str | None = None,
        analysis_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "event_type": event_type,
            "status": status,
            "message": message,
            "repository_id": repository_id,
            "repository_name": repository_name,
            "delivery_id": delivery_id,
            "analysis_run_id": analysis_run_id,
            "metadata": metadata or {},
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
        event_type: str | None = None,
        repository_id: str | None = None,
        sort: Literal["created_at"] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if event_type:
            query["event_type"] = event_type
        if repository_id:
            query["repository_id"] = repository_id
        sort_dir = -1 if order == "desc" else 1
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort(sort, sort_dir).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total
