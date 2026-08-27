from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_analysis_settings_service,
    get_members_service,
    get_organization_settings_service,
    require_permission,
)
from app.core.authorization import MembershipContext
from app.schemas.analysis_settings import AnalysisSettingsResponse
from app.schemas.invitations import InvitationCreateRequest, InvitationResponse
from app.schemas.members import MemberResponse, MemberRoleUpdateRequest
from app.schemas.organization_settings import OrganizationOverviewResponse, OrganizationUpdateRequest
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.analysis_settings import AnalysisSettingsService
from app.services.members import MembersService
from app.services.organization_settings import OrganizationSettingsService

router = APIRouter(prefix="/organization", tags=["organization"])


@router.get("", response_model=OrganizationOverviewResponse)
async def get_organization(
    context: Annotated[MembershipContext, Depends(require_permission("settings.read"))],
    service: Annotated[OrganizationSettingsService, Depends(get_organization_settings_service)],
) -> OrganizationOverviewResponse:
    overview = await service.get_overview(context.organization_id, role=context.role.value)
    if not overview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return overview


@router.patch("", response_model=OrganizationOverviewResponse)
async def update_organization(
    payload: OrganizationUpdateRequest,
    context: Annotated[MembershipContext, Depends(require_permission("settings.update"))],
    service: Annotated[OrganizationSettingsService, Depends(get_organization_settings_service)],
) -> OrganizationOverviewResponse:
    try:
        overview = await service.update_organization(
            context.organization_id,
            payload,
            actor_user_id=context.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not overview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return overview


@router.get("/members", response_model=PaginatedResponse[MemberResponse])
async def list_members(
    context: Annotated[MembershipContext, Depends(require_permission("members.read"))],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[MembersService, Depends(get_members_service)],
    role: str | None = None,
    q: str | None = None,
) -> PaginatedResponse[MemberResponse]:
    return await service.list_members(
        context.organization_id,
        current_user_id=context.user_id,
        page=pagination.page,
        page_size=pagination.page_size,
        role=role,
        q=q,
    )


@router.patch("/members/{membership_id}", response_model=MemberResponse)
async def update_member_role(
    membership_id: str,
    payload: MemberRoleUpdateRequest,
    context: Annotated[MembershipContext, Depends(require_permission("members.update_role"))],
    service: Annotated[MembersService, Depends(get_members_service)],
) -> MemberResponse:
    try:
        member = await service.update_member_role(
            context.organization_id,
            membership_id,
            payload,
            actor_user_id=context.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
    return member


@router.delete("/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    membership_id: str,
    context: Annotated[MembershipContext, Depends(require_permission("members.remove"))],
    service: Annotated[MembersService, Depends(get_members_service)],
) -> None:
    try:
        deleted = await service.remove_member(
            context.organization_id,
            membership_id,
            actor_user_id=context.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    context: Annotated[MembershipContext, Depends(require_permission("members.read"))],
    service: Annotated[MembersService, Depends(get_members_service)],
) -> list[InvitationResponse]:
    return await service.list_invitations(context.organization_id)


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    payload: InvitationCreateRequest,
    context: Annotated[MembershipContext, Depends(require_permission("members.invite"))],
    service: Annotated[MembersService, Depends(get_members_service)],
) -> InvitationResponse:
    try:
        return await service.create_invitation(
            context.organization_id,
            payload,
            actor_user_id=context.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/invitations/{invitation_id}", response_model=InvitationResponse)
async def revoke_invitation(
    invitation_id: str,
    context: Annotated[MembershipContext, Depends(require_permission("members.invite"))],
    service: Annotated[MembersService, Depends(get_members_service)],
) -> InvitationResponse:
    revoked = await service.revoke_invitation(
        context.organization_id,
        invitation_id,
        actor_user_id=context.user_id,
    )
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    return revoked


@router.get("/analysis-settings", response_model=AnalysisSettingsResponse)
async def get_analysis_settings(
    _: Annotated[MembershipContext, Depends(require_permission("analysis_settings.read"))],
    service: Annotated[AnalysisSettingsService, Depends(get_analysis_settings_service)],
) -> AnalysisSettingsResponse:
    return service.get_settings()
