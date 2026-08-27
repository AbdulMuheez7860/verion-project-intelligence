from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError


class NotificationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["notifications"]

    async def create(
        self,
        *,
        organization_id: str,
        user_id: str,
        notification_type: str,
        severity: str,
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
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "user_id": user_id,
            "type": notification_type,
            "severity": severity,
            "title": title,
            "body": body,
            "href": href,
            "repository_id": repository_id,
            "repository_name": repository_name,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "idempotency_key": idempotency_key,
            "read_at": None,
            "created_at": now,
        }
        try:
            await self._collection.insert_one(doc)
        except DuplicateKeyError:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_for_user(
        self,
        *,
        organization_id: str,
        user_id: str,
        skip: int,
        limit: int,
        unread_only: bool = False,
        notification_type: str | None = None,
        sort: Literal["created_at", "severity"] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {
            "organization_id": organization_id,
            "user_id": user_id,
        }
        if unread_only:
            query["read_at"] = None
        if notification_type:
            query["type"] = notification_type

        sort_dir = -1 if order == "desc" else 1
        sort_field = "created_at" if sort == "created_at" else "severity"
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total

    async def count_unread(self, *, organization_id: str, user_id: str) -> int:
        return await self._collection.count_documents(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "read_at": None,
            },
        )

    async def mark_read(
        self,
        *,
        notification_id: str,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one_and_update(
            {
                "_id": ObjectId(notification_id),
                "organization_id": organization_id,
                "user_id": user_id,
            },
            {"$set": {"read_at": datetime.now(UTC)}},
            return_document=True,
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def mark_all_read(self, *, organization_id: str, user_id: str) -> int:
        result = await self._collection.update_many(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "read_at": None,
            },
            {"$set": {"read_at": datetime.now(UTC)}},
        )
        return result.modified_count
