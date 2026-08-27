from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError


class WebhookDeliveryRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["webhook_deliveries"]

    async def record_if_new(self, delivery_id: str, *, event: str, organization_id: str) -> bool:
        """Return True if this delivery is new and should be processed."""
        now = datetime.now(UTC)
        try:
            await self._collection.insert_one(
                {
                    "_id": delivery_id,
                    "event": event,
                    "organization_id": organization_id,
                    "received_at": now,
                },
            )
            return True
        except DuplicateKeyError:
            return False
