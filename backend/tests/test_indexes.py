from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.database import get_database
from app.core.indexes import ensure_indexes
from app.repositories.webhook_deliveries import WebhookDeliveryRepository


@pytest.mark.asyncio
async def test_ensure_indexes_succeeds(client: AsyncClient):
    db = get_database()
    await ensure_indexes(db)


@pytest.mark.asyncio
async def test_webhook_deliveries_rely_on_default_unique_id_index(client: AsyncClient):
    db = get_database()
    await ensure_indexes(db)
    await db["webhook_deliveries"].delete_many({})

    # Materialize the collection; MongoDB then exposes the automatic _id_ index.
    await db["webhook_deliveries"].insert_one(
        {
            "_id": "__index-probe__",
            "event": "probe",
            "organization_id": "org-probe",
            "received_at": datetime.now(UTC),
        },
    )
    await db["webhook_deliveries"].delete_one({"_id": "__index-probe__"})

    indexes = await db["webhook_deliveries"].index_information()

    assert "_id_" in indexes
    assert set(indexes) == {"_id_"}


@pytest.mark.asyncio
async def test_webhook_delivery_record_if_new_is_idempotent(client: AsyncClient):
    repo = WebhookDeliveryRepository(get_database())

    assert await repo.record_if_new("gh-delivery-abc", event="push", organization_id="org-1") is True
    assert await repo.record_if_new("gh-delivery-abc", event="push", organization_id="org-1") is False
