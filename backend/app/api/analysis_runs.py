from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import RequireMember, RequireViewer, get_analysis_runs_service, get_audit_log_service
from app.schemas.analysis_runs import (
    AnalysisRunActionResponse,
    AnalysisRunDetailResponse,
    AnalysisRunListItem,
    AnalysisRunSortField,
    AnalysisRunStatusFilter,
    AnalysisRunTriggerFilter,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.analysis_runs import AnalysisRunsService
from app.services.audit_logs import AuditLogService

router = APIRouter(tags=["analysis-runs"])


@router.get("/analysis-runs", response_model=PaginatedResponse[AnalysisRunListItem])
async def list_analysis_runs(
    context: RequireViewer,
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
    repository_id: Annotated[str | None, Query(alias="repositoryId")] = None,
    status_filter: Annotated[AnalysisRunStatusFilter | None, Query(alias="status")] = None,
    trigger: Annotated[AnalysisRunTriggerFilter | None, Query()] = None,
    q: Annotated[str | None, Query(description="Search repository name or commit SHA")] = None,
    started_from: Annotated[str | None, Query(alias="from")] = None,
    started_to: Annotated[str | None, Query(alias="to")] = None,
    sort: Annotated[AnalysisRunSortField, Query()] = "started",
    order: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> PaginatedResponse[AnalysisRunListItem]:
    if started_from:
        _validate_iso_date(started_from, "from")
    if started_to:
        _validate_iso_date(started_to, "to")
    return await service.list_runs(
        context.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        repository_id=repository_id,
        status=status_filter,
        trigger=trigger,
        q=q,
        started_from=started_from,
        started_to=started_to,
        sort=sort,
        order=order,
    )


@router.get("/analysis-runs/{analysis_id}", response_model=AnalysisRunDetailResponse)
async def get_analysis_run(
    analysis_id: str,
    context: RequireViewer,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    detail = await service.get_run_detail(
        analysis_id,
        context.organization_id,
        role=context.role.value,
    )
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")
    return detail


@router.post("/analysis-runs/{analysis_id}/retry", response_model=AnalysisRunActionResponse)
async def retry_analysis_run(
    analysis_id: str,
    context: RequireMember,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
    audit: Annotated[AuditLogService, Depends(get_audit_log_service)],
) -> AnalysisRunActionResponse:
    try:
        result = await service.retry_run(analysis_id, context.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")
    await audit.record(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="analysis.retried",
        resource_type="analysis_run",
        resource_id=result.analysis_run_id or analysis_id,
    )
    return result


@router.post("/analysis-runs/{analysis_id}/cancel", response_model=AnalysisRunActionResponse)
async def cancel_analysis_run(
    analysis_id: str,
    context: RequireMember,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
    audit: Annotated[AuditLogService, Depends(get_audit_log_service)],
) -> AnalysisRunActionResponse:
    try:
        result = await service.cancel_run(analysis_id, context.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")
    await audit.record(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="analysis.cancelled",
        resource_type="analysis_run",
        resource_id=analysis_id,
    )
    return result


def _validate_iso_date(value: str, field: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field} date format. Use ISO 8601.",
        ) from exc
