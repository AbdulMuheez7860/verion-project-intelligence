from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import RequireMember, get_ai_assistant_service
from app.core.redis import get_redis
from app.integrations.llm.base import (
    LLMNotConfiguredError,
    LLMProviderError,
)
from app.lib.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.schemas.ai_assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantStatusResponse,
)
from app.services.ai_assistant import AIAssistantService


router = APIRouter(tags=["ai-assistant"])


# Bounds how many LLM-backed chat calls one membership can trigger
# per window.
CHAT_RATE_LIMIT = 20
CHAT_RATE_WINDOW_SECONDS = 60 * 10


@router.get(
    "/repositories/{repository_id}/assistant/status",
    response_model=AssistantStatusResponse,
)
async def assistant_status(
    repository_id: str,
    context: RequireMember,
    service: Annotated[
        AIAssistantService,
        Depends(get_ai_assistant_service),
    ],
) -> AssistantStatusResponse:
    return await service.get_status(
        repository_id,
        context.organization_id,
    )


@router.post(
    "/repositories/{repository_id}/assistant/chat",
    response_model=AssistantChatResponse,
)
async def assistant_chat(
    repository_id: str,
    body: AssistantChatRequest,
    context: RequireMember,
    service: Annotated[
        AIAssistantService,
        Depends(get_ai_assistant_service),
    ],
) -> AssistantChatResponse:
    try:
        await enforce_rate_limit(
            get_redis(),
            # Rate-limit per membership, not per repository.
            key=f"assistant-chat:{context.organization_id}:{context.user_id}",
            limit=CHAT_RATE_LIMIT,
            window_seconds=CHAT_RATE_WINDOW_SECONDS,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many assistant requests. "
                f"Try again in {exc.retry_after_seconds} seconds."
            ),
        ) from exc

    try:
        return await service.chat(
            repository_id=repository_id,
            organization_id=context.organization_id,
            message=body.message,
            history=body.history,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LLMNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc