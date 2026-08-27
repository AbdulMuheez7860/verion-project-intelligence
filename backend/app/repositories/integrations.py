from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class IntegrationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["integrations"]

    async def get_github_by_organization(self, organization_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"organization_id": organization_id, "provider": "github"},
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def upsert_github(
        self,
        *,
        organization_id: str,
        github_user_id: int,
        github_login: str,
        access_token_encrypted: str,
        scopes: list[str],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "organization_id": organization_id,
            "provider": "github",
            "status": "connected",
            "github_user_id": github_user_id,
            "github_login": github_login,
            "access_token_encrypted": access_token_encrypted,
            "scopes": scopes,
            "updated_at": now,
        }
        result = await self._collection.find_one_and_update(
            {"organization_id": organization_id, "provider": "github"},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )
        result["id"] = str(result.pop("_id"))
        return result

    async def delete_github(self, organization_id: str) -> bool:
        result = await self._collection.delete_one(
            {"organization_id": organization_id, "provider": "github"},
        )
        return result.deleted_count > 0

    async def get_by_github_user_id(self, github_user_id: int) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"provider": "github", "github_user_id": github_user_id},
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc
