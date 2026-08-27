from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

DEFAULT_PREFERENCES = {
    "security_alerts": True,
    "dependency_alerts": True,
    "pr_risk_alerts": True,
    "analysis_alerts": True,
    "regression_alerts": True,
    "workspace_alerts": True,
}


class NotificationPreferencesRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["notification_preferences"]

    async def get_or_create(self, *, organization_id: str, user_id: str) -> dict[str, Any]:
        doc = await self._collection.find_one(
            {"organization_id": organization_id, "user_id": user_id},
        )
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return doc

        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "user_id": user_id,
            **DEFAULT_PREFERENCES,
            "created_at": now,
            "updated_at": now,
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def update(
        self,
        *,
        organization_id: str,
        user_id: str,
        updates: dict[str, bool],
    ) -> dict[str, Any]:
        await self.get_or_create(organization_id=organization_id, user_id=user_id)
        now = datetime.now(UTC)
        doc = await self._collection.find_one_and_update(
            {"organization_id": organization_id, "user_id": user_id},
            {"$set": {**updates, "updated_at": now}},
            return_document=True,
        )
        if not doc:
            raise ValueError("Notification preferences not found.")
        doc["id"] = str(doc.pop("_id"))
        return doc
