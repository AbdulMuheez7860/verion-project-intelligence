from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import RequireAdmin, RequireViewer, get_audit_log_service, get_github_integration_service, get_notification_event_service, get_oauth_state_store
from app.core.config import get_settings
from app.core.redis import OAuthStateStore
from app.schemas.integration import (
    GitHubConnectResponse,
    GitHubIntegrationResponse,
    GitHubRepositoryOption,
)
from app.services.audit_logs import AuditLogService
from app.services.github_integration import GitHubIntegrationService
from app.services.notification_events import NotificationEventService

router = APIRouter(prefix="/integrations/github", tags=["integrations"])


def _ensure_github_configured() -> None:
    if not get_settings().github_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
        )


@router.get("", response_model=GitHubIntegrationResponse)
async def get_github_integration(
    context: RequireViewer,
    service: Annotated[GitHubIntegrationService, Depends(get_github_integration_service)],
) -> GitHubIntegrationResponse:
    return await service.get_status(context.organization_id)


@router.post("/connect", response_model=GitHubConnectResponse)
async def connect_github(
    context: RequireAdmin,
    service: Annotated[GitHubIntegrationService, Depends(get_github_integration_service)],
    state_store: Annotated[OAuthStateStore, Depends(get_oauth_state_store)],
) -> GitHubConnectResponse:
    _ensure_github_configured()
    state = await state_store.create(context.organization_id, actor_user_id=context.user_id)
    return GitHubConnectResponse(authorize_url=service.build_authorize_url(state=state))


@router.get("/callback")
async def github_oauth_callback(
    service: Annotated[GitHubIntegrationService, Depends(get_github_integration_service)],
    state_store: Annotated[OAuthStateStore, Depends(get_oauth_state_store)],
    audit: Annotated[AuditLogService, Depends(get_audit_log_service)],
    notifications: Annotated[NotificationEventService, Depends(get_notification_event_service)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> Response:
    settings = get_settings()
    redirect_base = f"{settings.frontend_url}/app/settings/integrations"

    if error:
        return RedirectResponse(url=f"{redirect_base}?github=error&message={error}", status_code=302)
    if not code or not state:
        return RedirectResponse(url=f"{redirect_base}?github=error&message=missing_code", status_code=302)

    oauth_state = await state_store.consume(state)
    if not oauth_state:
        return RedirectResponse(url=f"{redirect_base}?github=error&message=invalid_state", status_code=302)

    organization_id = oauth_state["organization_id"]
    actor_user_id = oauth_state.get("actor_user_id")

    try:
        status_response = await service.complete_oauth(organization_id=organization_id, code=code)
    except Exception as exc:
        message = str(exc).replace(" ", "+")
        return RedirectResponse(url=f"{redirect_base}?github=error&message={message}", status_code=302)

    if actor_user_id:
        await audit.record(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="integration.connected",
            resource_type="integration",
            resource_id="github",
            metadata={"github_login": status_response.github_login},
        )
        await notifications.emit_workspace_event(
            organization_id=organization_id,
            notification_type="integration.connected",
            title="GitHub connected",
            body=f"GitHub integration connected as {status_response.github_login or 'unknown'}.",
            href="/app/settings/integrations",
            idempotency_key=f"integration.connected:{organization_id}",
            resource_type="integration",
            resource_id="github",
        )

    return RedirectResponse(url=f"{redirect_base}?github=connected", status_code=302)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_github(
    context: RequireAdmin,
    service: Annotated[GitHubIntegrationService, Depends(get_github_integration_service)],
    audit: Annotated[AuditLogService, Depends(get_audit_log_service)],
    notifications: Annotated[NotificationEventService, Depends(get_notification_event_service)],
) -> None:
    await service.disconnect(context.organization_id)
    await audit.record(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="integration.disconnected",
        resource_type="integration",
        resource_id="github",
    )
    await notifications.emit_workspace_event(
        organization_id=context.organization_id,
        notification_type="integration.disconnected",
        title="GitHub disconnected",
        body="GitHub integration was disconnected from this workspace.",
        href="/app/settings/integrations",
        idempotency_key=f"integration.disconnected:{context.organization_id}:{context.user_id}",
        resource_type="integration",
        resource_id="github",
    )


@router.get("/repositories", response_model=list[GitHubRepositoryOption])
async def list_github_repositories(
    context: RequireAdmin,
    service: Annotated[GitHubIntegrationService, Depends(get_github_integration_service)],
) -> list[GitHubRepositoryOption]:
    try:
        return await service.list_available_repositories(context.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
