import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import get_database
from app.integrations.github.webhooks import verify_github_signature
from app.repositories.repositories import RepositoryRepository
from app.workers.tasks.webhooks import process_github_webhook

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(request: Request) -> JSONResponse:
    payload_bytes = await request.body()
    settings = get_settings()

    event = request.headers.get("x-github-event")
    delivery_id = request.headers.get("x-github-delivery")
    signature = request.headers.get("x-hub-signature-256")

    if settings.webhook_verification_required:
        if not settings.github_webhook_secret:
            logger.error("Webhook verification required but GITHUB_WEBHOOK_SECRET is not configured.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook verification is not configured.",
            )
        if not verify_github_signature(payload_bytes, signature, settings.github_webhook_secret):
            logger.warning(
                "Rejected GitHub webhook with invalid signature",
                extra={"delivery_id": delivery_id, "event": event},
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")
    elif settings.github_webhook_secret:
        if not verify_github_signature(payload_bytes, signature, settings.github_webhook_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")

    if not event or not delivery_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing GitHub webhook headers.")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    repo_payload = payload.get("repository", {})
    if not isinstance(repo_payload, dict):
        return JSONResponse({"status": "ignored", "reason": "missing_repository"})

    full_name = repo_payload.get("full_name")
    if not isinstance(full_name, str) or "/" not in full_name:
        return JSONResponse({"status": "ignored", "reason": "missing_repository_name"})

    db = get_database()
    repo_repo = RepositoryRepository(db)
    repo_doc = await repo_repo.get_by_full_name(full_name)
    if not repo_doc:
        logger.info(
            "Ignored GitHub webhook for unconnected repository",
            extra={"delivery_id": delivery_id, "event": event, "repository": full_name},
        )
        return JSONResponse({"status": "ignored", "reason": "repository_not_connected"})

    organization_id = repo_doc.get("organization_id")
    if not isinstance(organization_id, str):
        return JSONResponse({"status": "ignored", "reason": "invalid_organization"})

    process_github_webhook.delay(
        delivery_id,
        event,
        organization_id,
        repo_doc["id"],
        payload,
    )
    logger.info(
        "Accepted GitHub webhook",
        extra={"delivery_id": delivery_id, "event": event, "organization_id": organization_id},
    )
    return JSONResponse({"status": "accepted"}, status_code=status.HTTP_202_ACCEPTED)
