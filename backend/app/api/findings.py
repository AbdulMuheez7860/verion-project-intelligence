from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    RequireMember,
    RequireViewer,
    get_finding_ai_service,
    get_findings_service,
)
from app.integrations.llm.base import (
    LLMNotConfiguredError,
    LLMProviderError,
)
from app.schemas.ai import FindingAIExplanation
from app.schemas.dependency_intelligence import DependencyIntelligenceResponse
from app.schemas.dependency_list import DependencyListParams
from app.schemas.findings import (
    DependencyResponse,
    DependencySummary,
    FindingDetailResponse,
    QualityFindingResponse,
    QualitySummary,
    SecurityFindingResponse,
    SecuritySummary,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.quality_intelligence import QualityIntelligenceResponse
from app.schemas.quality_list import QualityListParams
from app.schemas.security_intelligence import SecurityIntelligenceResponse
from app.schemas.security_list import SecurityListParams
from app.services.finding_ai import FindingAIService
from app.services.findings import FindingsService


router = APIRouter(prefix="/findings", tags=["findings"])


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------

@router.get(
    "/security/summary",
    response_model=SecuritySummary,
)
async def security_summary(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> SecuritySummary:
    return await service.security_summary(
        context.organization_id,
    )


@router.get(
    "/security/intelligence",
    response_model=SecurityIntelligenceResponse,
)
async def security_intelligence(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> SecurityIntelligenceResponse:
    return await service.security_intelligence(
        context.organization_id,
    )


@router.get(
    "/security/findings",
    response_model=PaginatedResponse[SecurityFindingResponse],
)
async def security_findings(
    context: RequireViewer,
    pagination: Annotated[
        PaginationParams,
        Depends(),
    ],
    filters: Annotated[
        SecurityListParams,
        Depends(),
    ],
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> PaginatedResponse[SecurityFindingResponse]:
    return await service.security_findings_paginated(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        q=filters.q,
        repository_id=filters.repository_id,
        severity=filters.severity,
        status=filters.status,
        category=filters.category,
        sort=filters.sort,
        order=filters.order,
    )


# ---------------------------------------------------------------------------
# QUALITY
# ---------------------------------------------------------------------------

@router.get(
    "/quality/summary",
    response_model=QualitySummary,
)
async def quality_summary(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> QualitySummary:
    return await service.quality_summary(
        context.organization_id,
    )


@router.get(
    "/code-quality/intelligence",
    response_model=QualityIntelligenceResponse,
)
async def code_quality_intelligence(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> QualityIntelligenceResponse:
    return await service.quality_intelligence(
        context.organization_id,
    )


@router.get(
    "/quality/intelligence",
    response_model=QualityIntelligenceResponse,
)
async def quality_intelligence(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> QualityIntelligenceResponse:
    return await service.quality_intelligence(
        context.organization_id,
    )


@router.get(
    "/quality/findings",
    response_model=PaginatedResponse[QualityFindingResponse],
)
async def quality_findings(
    context: RequireViewer,
    pagination: Annotated[
        PaginationParams,
        Depends(),
    ],
    filters: Annotated[
        QualityListParams,
        Depends(),
    ],
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> PaginatedResponse[QualityFindingResponse]:
    return await service.quality_findings_paginated(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        q=filters.q,
        repository_id=filters.repository_id,
        severity=filters.severity,
        status=filters.status,
        rule_id=filters.rule_id,
        sort=filters.sort,
        order=filters.order,
    )


# ---------------------------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------------------------

@router.get(
    "/dependencies/intelligence",
    response_model=DependencyIntelligenceResponse,
)
async def dependency_intelligence(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> DependencyIntelligenceResponse:
    return await service.dependency_intelligence(
        context.organization_id,
    )


@router.get(
    "/dependencies/summary",
    response_model=DependencySummary,
)
async def dependency_summary(
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> DependencySummary:
    return await service.dependency_summary(
        context.organization_id,
    )


@router.get(
    "/dependencies",
    response_model=PaginatedResponse[DependencyResponse],
)
async def dependencies(
    context: RequireViewer,
    pagination: Annotated[
        PaginationParams,
        Depends(),
    ],
    filters: Annotated[
        DependencyListParams,
        Depends(),
    ],
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> PaginatedResponse[DependencyResponse]:
    return await service.dependencies_paginated(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        q=filters.q,
        repository_id=filters.repository_id,
        status=filters.status,
        ecosystem=filters.ecosystem,
        severity=filters.severity,
        sort=filters.sort,
        order=filters.order,
    )


@router.get(
    "/dependencies/{dependency_id}",
    response_model=DependencyResponse,
)
async def get_dependency(
    dependency_id: str,
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> DependencyResponse:
    dependency = await service.get_dependency(
        dependency_id,
        context.organization_id,
    )

    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found.",
        )

    return dependency


# ---------------------------------------------------------------------------
# SINGLE FINDING
# ---------------------------------------------------------------------------

@router.get(
    "/{finding_id}",
    response_model=FindingDetailResponse,
)
async def get_finding(
    finding_id: str,
    context: RequireViewer,
    service: Annotated[
        FindingsService,
        Depends(get_findings_service),
    ],
) -> FindingDetailResponse:
    finding = await service.get_finding(
        finding_id,
        context.organization_id,
    )

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )

    return finding


# ---------------------------------------------------------------------------
# AI EXPLANATION
# ---------------------------------------------------------------------------

@router.post(
    "/{finding_id}/explain",
    response_model=FindingAIExplanation,
)
async def explain_finding(
    finding_id: str,
    context: RequireMember,
    ai_service: Annotated[
        FindingAIService,
        Depends(get_finding_ai_service),
    ],
    regenerate: Annotated[
        bool,
        Query(alias="regenerate"),
    ] = False,
) -> FindingAIExplanation:
    try:
        return await ai_service.explain_finding(
            finding_id,
            context.organization_id,
            regenerate=regenerate,
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