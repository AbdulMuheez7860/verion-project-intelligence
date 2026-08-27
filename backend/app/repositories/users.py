from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import hash_password
from app.utils.ids import new_id, slugify


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["users"]

    async def create(
        self,
        *,
        name: str,
        email: str,
        password: str,
        organization_id: str,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "name": name,
            "email": email.lower(),
            "password_hash": hash_password(password),
            "organization_id": organization_id,
            "timezone": timezone,
            "created_at": now,
            "updated_at": now,
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"email": email.lower()})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def update_profile(
        self,
        user_id: str,
        *,
        name: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any] | None:
        update: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if name is not None:
            update["name"] = name
        if timezone is not None:
            update["timezone"] = timezone
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update},
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def update_organization_id(self, user_id: str, organization_id: str) -> bool:
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"organization_id": organization_id, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0

    async def update_password(self, user_id: str, password: str) -> bool:
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_hash": hash_password(password),
                    "updated_at": datetime.now(UTC),
                },
            },
        )
        return result.modified_count > 0


class OrganizationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["organizations"]

    async def create(self, *, name: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "name": name,
            "slug": slugify(name),
            "created_at": now,
            "updated_at": now,
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_id(self, organization_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"_id": ObjectId(organization_id)})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def update_name(self, organization_id: str, *, name: str) -> dict[str, Any] | None:
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(organization_id)},
            {"$set": {"name": name, "updated_at": datetime.now(UTC)}},
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result
