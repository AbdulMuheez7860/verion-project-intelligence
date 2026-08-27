import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PasswordResetTokenRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["password_reset_tokens"]

    async def create(self, *, user_id: str, ttl_seconds: int) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = datetime.now(UTC)
        await self._collection.insert_one(
            {
                "_id": token_hash,
                "user_id": user_id,
                "created_at": now,
                "expires_at": now + timedelta(seconds=ttl_seconds),
                "used_at": None,
            },
        )
        return raw_token

    async def consume(self, raw_token: str) -> dict[str, Any] | None:
        token_hash = _hash_token(raw_token)
        now = datetime.now(UTC)
        doc = await self._collection.find_one_and_update(
            {
                "_id": token_hash,
                "used_at": None,
                "expires_at": {"$gt": now},
            },
            {"$set": {"used_at": now}},
            return_document=True,
        )
        return doc
