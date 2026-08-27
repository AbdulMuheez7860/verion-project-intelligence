from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.auth import MembershipRole


class MembershipRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["memberships"]

    async def create(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: MembershipRole,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "user_id": user_id,
            "organization_id": organization_id,
            "role": role.value,
            "created_at": now,
            "updated_at": now,
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_id(self, membership_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"_id": ObjectId(membership_id)})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_for_user_and_organization(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"user_id": user_id, "organization_id": organization_id},
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_by_organization(
        self,
        organization_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
        role: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if role:
            query["role"] = role
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("created_at", 1).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total

    async def count_by_organization(self, organization_id: str) -> int:
        return await self._collection.count_documents({"organization_id": organization_id})

    async def count_admins(self, organization_id: str) -> int:
        return await self._collection.count_documents(
            {"organization_id": organization_id, "role": {"$in": ["admin", "owner"]}},
        )

    async def update_role(
        self,
        membership_id: str,
        organization_id: str,
        *,
        role: MembershipRole,
    ) -> dict[str, Any] | None:
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(membership_id), "organization_id": organization_id},
            {"$set": {"role": role.value, "updated_at": datetime.now(UTC)}},
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def delete_membership(self, membership_id: str, organization_id: str) -> bool:
        result = await self._collection.delete_one(
            {"_id": ObjectId(membership_id), "organization_id": organization_id},
        )
        return result.deleted_count > 0
