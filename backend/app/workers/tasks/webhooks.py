import asyncio
from typing import Any

from app.core.database import close_client
from app.repositories.repositories import RepositoryRepository
from app.repositories.webhook_deliveries import WebhookDeliveryRepository
from app.workers.celery_app import celery_app
from app.workers.tasks.analysis import enqueue_analysis


@celery_app.task(name="verion.process_github_webhook")
def process_github_webhook(
    delivery_id: str,
    event: str,
    organization_id: str,
    repository_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return asyncio.run(
        _process_github_webhook_async(delivery_id, event, organization_id, repository_id, payload),
    )


async def _process_github_webhook_async(
    delivery_id: str,
    event: str,
    organization_id: str,
    repository_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from app.core.database import get_database

    db = get_database()
    deliveries = WebhookDeliveryRepository(db)
    is_new = await deliveries.record_if_new(
        delivery_id,
        event=event,
        organization_id=organization_id,
    )
    if not is_new:
        return {"status": "duplicate", "delivery_id": delivery_id}

    trigger = f"webhook:{event}"
    if event in {"push", "pull_request"}:
        enqueue_analysis(repository_id, organization_id, trigger=trigger)
        return {"status": "queued", "delivery_id": delivery_id, "event": event}

    return {"status": "ignored", "delivery_id": delivery_id, "event": event}


async def _noop() -> None:
    await close_client()
