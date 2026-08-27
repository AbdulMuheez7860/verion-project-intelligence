from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.auth import MembershipRole

INVITATION_TTL_DAYS = 7


class InvitationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["invitations"]

    async def create(
        self,
        *,
        organization_id: str,
        email: str,
        role: MembershipRole,
        invited_by_user_id: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "email": email.lower(),
            "role": role.value,
            "status": "pending",
            "invited_by_user_id": invited_by_user_id,
            "created_at": now,
            "expires_at": now + timedelta(days=INVITATION_TTL_DAYS),
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_by_organization(self, organization_id: str) -> list[dict[str, Any]]:
        cursor = self._collection.find({"organization_id": organization_id}).sort("created_at", -1)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def get_pending_by_email(self, organization_id: str, email: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {
                "organization_id": organization_id,
                "email": email.lower(),
                "status": "pending",
            },
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_id(self, invitation_id: str, organization_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"_id": ObjectId(invitation_id), "organization_id": organization_id},
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def revoke(self, invitation_id: str, organization_id: str) -> dict[str, Any] | None:
        result = await self._collection.find_one_and_update(
            {
                "_id": ObjectId(invitation_id),
                "organization_id": organization_id,
                "status": "pending",
            },
            {"$set": {"status": "revoked", "updated_at": datetime.now(UTC)}},
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def mark_accepted(self, invitation_id: str) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(invitation_id)},
            {"$set": {"status": "accepted", "updated_at": datetime.now(UTC)}},
        )

    async def get_valid_pending_by_email(self, email: str) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        doc = await self._collection.find_one(
            {
                "email": email.lower(),
                "status": "pending",
                "expires_at": {"$gt": now},
            },
            sort=[("created_at", -1)],
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc
