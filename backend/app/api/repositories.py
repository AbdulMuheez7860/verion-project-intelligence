from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    RequireAdmin,
    RequireMember,
    RequireViewer,
    get_repository_intelligence_service,
    get_repository_service,
)
from app.schemas.findings import DependencyResponse, QualityFindingResponse, SecurityFindingResponse
from app.schemas.integration import ConnectRepositoryRequest
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.repository import (
    AnalyzeResponse,
    AnalysisRunDetailResponse,
    AnalysisRunResponse,
    RepositoryPullRequestResponse,
    RepositoryResponse,
)
from app.schemas.repository_intelligence import HealthHistoryResponse, RepositoryIntelligenceResponse
from app.services.repositories import RepositoryService
from app.services.repository_intelligence import RepositoryIntelligenceService


router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get(
    "",
    response_model=PaginatedResponse[RepositoryResponse],
)
async def list_repositories(
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
    q: str | None = Query(default=None),
    analysis_status: str | None = Query(default=None, alias="analysisStatus"),
    risk_level: str | None = Query(default=None, alias="riskLevel"),
    security_status: str | None = Query(default=None, alias="securityStatus"),
    sort: str = Query(default="name"),
    order: str = Query(default="asc"),
) -> PaginatedResponse[RepositoryResponse]:
    return await service.list_repositories_paginated(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        q=q,
        analysis_status=analysis_status,
        risk_level=risk_level,
        security_status=security_status,
        sort=sort,
        order=order,
    )


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_repository(
    context: RequireMember,
    payload: ConnectRepositoryRequest,
    service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> RepositoryResponse:
    try:
        return await service.connect_repository(
            context.organization_id,
            payload.github_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{repository_id}/intelligence",
    response_model=RepositoryIntelligenceResponse,
)
async def repository_intelligence(
    repository_id: str,
    context: RequireViewer,
    intelligence: Annotated[
        RepositoryIntelligenceService,
        Depends(get_repository_intelligence_service),
    ],
) -> RepositoryIntelligenceResponse:
    result = await intelligence.get_intelligence(
        repository_id,
        context.organization_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return result


@router.get(
    "/{repository_id}/health-history",
    response_model=HealthHistoryResponse,
)
async def repository_health_history(
    repository_id: str,
    context: RequireViewer,
    intelligence: Annotated[
        RepositoryIntelligenceService,
        Depends(get_repository_intelligence_service),
    ],
) -> HealthHistoryResponse:
    result = await intelligence.list_health_history(
        repository_id,
        context.organization_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return result


@router.get(
    "/{repository_id}/analysis-runs",
    response_model=PaginatedResponse[AnalysisRunResponse],
)
async def repository_analysis_runs(
    repository_id: str,
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> PaginatedResponse[AnalysisRunResponse]:
    result = await service.list_analysis_runs_paginated(
        repository_id,
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return result


@router.get(
    "/{repository_id}/analysis-runs/{analysis_id}",
    response_model=AnalysisRunDetailResponse,
)
async def repository_analysis_run_detail(
    repository_id: str,
    analysis_id: str,
    context: RequireViewer,
    intelligence: Annotated[
        RepositoryIntelligenceService,
        Depends(get_repository_intelligence_service),
    ],
) -> AnalysisRunDetailResponse:
    result = await intelligence.get_analysis_run_detail(
        repository_id,
        analysis_id,
        context.organization_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found.",
        )
    return result


@router.get(
    "/{repository_id}/findings",
    response_model=PaginatedResponse[SecurityFindingResponse | QualityFindingResponse],
)
async def repository_findings(
    repository_id: str,
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    intelligence: Annotated[
        RepositoryIntelligenceService,
        Depends(get_repository_intelligence_service),
    ],
    category: Literal["security", "quality"] | None = Query(default=None),
    severity: str | None = Query(default=None),
) -> PaginatedResponse[SecurityFindingResponse | QualityFindingResponse]:
    result = await intelligence.list_findings_paginated(
        repository_id,
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        category=category,
        severity=severity,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return result


@router.get(
    "/{repository_id}/dependencies",
    response_model=PaginatedResponse[DependencyResponse],
)
async def repository_dependencies(
    repository_id: str,
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    intelligence: Annotated[
        RepositoryIntelligenceService,
        Depends(get_repository_intelligence_service),
    ],
) -> PaginatedResponse[DependencyResponse]:
    result = await intelligence.list_dependencies_paginated(
        repository_id,
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return result


@router.get(
    "/{repository_id}/pull-requests",
    response_model=PaginatedResponse[RepositoryPullRequestResponse],
)
async def repository_pull_requests(
    repository_id: str,
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    intelligence: Annotated[
        RepositoryIntelligenceService,
        Depends(get_repository_intelligence_service),
    ],
) -> PaginatedResponse[RepositoryPullRequestResponse]:
    result = await intelligence.list_pull_requests_paginated(
        repository_id,
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return result


@router.post(
    "/{repository_id}/analyze",
    response_model=AnalyzeResponse,
)
async def analyze_repository(
    repository_id: str,
    context: RequireMember,
    service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> AnalyzeResponse:
    result = await service.queue_analysis(
        repository_id,
        context.organization_id,
        trigger="manual",
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    if result == "already_queued":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already queued or running for this repository.",
        )
    return AnalyzeResponse(status=result)


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
)
async def get_repository(
    repository_id: str,
    context: RequireViewer,
    service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> RepositoryResponse:
    repository = await service.get_repository(
        repository_id,
        context.organization_id,
    )
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    return repository


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect_repository(
    repository_id: str,
    context: RequireAdmin,
    service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> None:
    deleted = await service.disconnect_repository(
        repository_id,
        context.organization_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
