from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    RequireMember,
    RequireViewer,
    get_github_integration_service,
    get_pull_request_intelligence_service,
    get_pull_request_risk_service,
    get_repository_service,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.pull_request_intelligence import PullRequestIntelligenceResponse, PullRequestListItem
from app.schemas.pull_request_list import PullRequestListParams
from app.schemas.repository import PullRequestDetailResponse, RiskScore
from app.services.github_integration import GitHubIntegrationService
from app.services.pr_risk_service import PullRequestRiskService
from app.services.pull_request_intelligence import PullRequestIntelligenceService
from app.services.repositories import RepositoryService

router = APIRouter(tags=["pull-requests"])


@router.get("/pull-requests", response_model=PaginatedResponse[PullRequestListItem])
async def list_pull_requests(
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    filters: Annotated[PullRequestListParams, Depends()],
    service: Annotated[PullRequestIntelligenceService, Depends(get_pull_request_intelligence_service)],
) -> PaginatedResponse[PullRequestListItem]:
    return await service.list_pull_requests_paginated(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        q=filters.q,
        repository_id=filters.repository_id,
        status=filters.status,
        risk_level=filters.risk_level,
        verdict=filters.verdict,
        author=filters.author,
        sort=filters.sort,
        order=filters.order,
    )


@router.get("/pull-requests/{pr_id}", response_model=PullRequestDetailResponse)
async def get_pull_request(
    pr_id: int,
    context: RequireViewer,
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> PullRequestDetailResponse:
    pr = await service.get_pull_request(pr_id, context.organization_id)
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pull request not found.")
    return pr


@router.get("/pull-requests/{pr_id}/intelligence", response_model=PullRequestIntelligenceResponse)
async def get_pull_request_intelligence(
    pr_id: int,
    context: RequireViewer,
    service: Annotated[PullRequestIntelligenceService, Depends(get_pull_request_intelligence_service)],
) -> PullRequestIntelligenceResponse:
    intelligence = await service.get_intelligence(pr_id, context.organization_id)
    if not intelligence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pull request not found.")
    return intelligence


@router.get("/pull-requests/{pr_id}/risk", response_model=RiskScore)
async def get_pull_request_risk(
    pr_id: int,
    context: RequireViewer,
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> RiskScore:
    risk = await service.get_pull_request_risk(pr_id, context.organization_id)
    if not risk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk analysis not available.")
    return risk


@router.post("/pull-requests/{pr_id}/reanalyze")
async def reanalyze_pull_request(
    pr_id: int,
    context: RequireMember,
    risk_service: Annotated[PullRequestRiskService, Depends(get_pull_request_risk_service)],
    github: Annotated[GitHubIntegrationService, Depends(get_github_integration_service)],
) -> dict[str, str]:
    try:
        client = await github.get_github_client(context.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = await risk_service.score_pull_request_by_id(
        github_id=pr_id,
        organization_id=context.organization_id,
        client=client,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pull request not found.")
    return {"status": "complete"}
