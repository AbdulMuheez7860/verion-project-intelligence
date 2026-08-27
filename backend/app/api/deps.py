from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authorization import MembershipContext, ROLE_RANK
from app.core.config import get_settings
from app.core.database import get_db
from app.core.permissions import Permission, can
from app.core.redis import OAuthStateStore, get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)

from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.integrations import IntegrationRepository
from app.repositories.invitations import InvitationRepository
from app.repositories.memberships import MembershipRepository
from app.repositories.notification_preferences import (
    NotificationPreferencesRepository,
)
from app.repositories.notifications import NotificationRepository
from app.repositories.password_reset_tokens import PasswordResetTokenRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.repositories.users import OrganizationRepository, UserRepository

from app.schemas.auth import MembershipRole, SessionResponse, UserResponse

from app.services.ai_assistant import AIAssistantService
from app.services.analysis_runs import AnalysisRunsService
from app.services.analysis_settings import AnalysisSettingsService
from app.services.analytics import AnalyticsService
from app.services.audit_logs import AuditLogService
from app.services.auth import AuthService
from app.services.dashboard import DashboardService
from app.services.finding_ai import FindingAIService
from app.services.findings import FindingsService
from app.services.github_integration import GitHubIntegrationService
from app.services.historical_intelligence import HistoricalIntelligenceService
from app.services.members import MembersService
from app.services.notification_events import NotificationEventService
from app.services.notifications import NotificationService
from app.services.organization_settings import OrganizationSettingsService
from app.services.password_reset import PasswordResetService
from app.services.pr_risk_service import PullRequestRiskService
from app.services.pull_request_intelligence import PullRequestIntelligenceService
from app.services.report_generation import ReportGenerationService
from app.services.repositories import RepositoryService
from app.services.repository_intelligence import RepositoryIntelligenceService


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

async def get_database(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> AsyncIOMotorDatabase:
    return db


# ---------------------------------------------------------------------------
# Authentication / user services
# ---------------------------------------------------------------------------

def get_auth_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AuthService:
    return AuthService(
        UserRepository(db),
        OrganizationRepository(db),
        MembershipRepository(db),
    )


def get_password_reset_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> PasswordResetService:
    return PasswordResetService(
        UserRepository(db),
        PasswordResetTokenRepository(db),
    )


# ---------------------------------------------------------------------------
# GitHub / Repository services
# ---------------------------------------------------------------------------

def get_github_integration_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> GitHubIntegrationService:
    return GitHubIntegrationService(
        IntegrationRepository(db),
        RepositoryRepository(db),
    )


def get_repository_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    github_service: Annotated[
        GitHubIntegrationService,
        Depends(get_github_integration_service),
    ],
) -> RepositoryService:
    return RepositoryService(
        RepositoryRepository(db),
        PullRequestRepository(db),
        github_service,
        AnalysisRunRepository(db),
    )


def get_pull_request_intelligence_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> PullRequestIntelligenceService:
    repo_repo = RepositoryRepository(db)

    findings_service = FindingsService(
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        repo_repo,
    )

    return PullRequestIntelligenceService(
        PullRequestRepository(db),
        FindingRepository(db),
        repo_repo,
        findings_service,
    )


def get_pull_request_risk_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> PullRequestRiskService:
    return PullRequestRiskService(
        PullRequestRepository(db),
        FindingRepository(db),
        RepositoryRepository(db),
    )


def get_repository_intelligence_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    github_service: Annotated[
        GitHubIntegrationService,
        Depends(get_github_integration_service),
    ],
) -> RepositoryIntelligenceService:
    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)

    repository_service = RepositoryService(
        repo_repo,
        pr_repo,
        github_service,
        AnalysisRunRepository(db),
    )

    findings_service = FindingsService(
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        repo_repo,
    )

    return RepositoryIntelligenceService(
        repo_repo,
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        pr_repo,
        IntegrationRepository(db),
        repository_service,
        findings_service,
    )


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------

def get_oauth_state_store() -> OAuthStateStore:
    return OAuthStateStore(get_redis())


# ---------------------------------------------------------------------------
# Analysis services
# ---------------------------------------------------------------------------

def get_analysis_runs_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    github_service: Annotated[
        GitHubIntegrationService,
        Depends(get_github_integration_service),
    ],
) -> AnalysisRunsService:
    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)

    repository_service = RepositoryService(
        repo_repo,
        pr_repo,
        github_service,
        AnalysisRunRepository(db),
    )

    return AnalysisRunsService(
        AnalysisRunRepository(db),
        AnalysisSnapshotRepository(db),
        repo_repo,
        repository_service,
        FindingRepository(db),
    )


def get_analysis_settings_service() -> AnalysisSettingsService:
    return AnalysisSettingsService()


# ---------------------------------------------------------------------------
# Dashboard / Analytics
# ---------------------------------------------------------------------------

def get_dashboard_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> DashboardService:
    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)

    github_service = GitHubIntegrationService(
        IntegrationRepository(db),
        repo_repo,
    )

    repository_service = RepositoryService(
        repo_repo,
        pr_repo,
        github_service,
        AnalysisRunRepository(db),
    )

    return DashboardService(
        repo_repo,
        pr_repo,
        repository_service,
        FindingRepository(db),
        AnalysisRunRepository(db),
        DependencyRepository(db),
    )


def get_historical_intelligence_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> HistoricalIntelligenceService:
    return HistoricalIntelligenceService(
        AnalysisSnapshotRepository(db),
        RepositoryRepository(db),
        AnalysisRunRepository(db),
        PullRequestRepository(db),
    )


def get_analytics_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    historical: Annotated[
        HistoricalIntelligenceService,
        Depends(get_historical_intelligence_service),
    ],
) -> AnalyticsService:
    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)

    github_service = GitHubIntegrationService(
        IntegrationRepository(db),
        repo_repo,
    )

    repository_service = RepositoryService(
        repo_repo,
        pr_repo,
        github_service,
        AnalysisRunRepository(db),
    )

    dashboard_service = DashboardService(
        repo_repo,
        pr_repo,
        repository_service,
        FindingRepository(db),
        AnalysisRunRepository(db),
        DependencyRepository(db),
    )

    return AnalyticsService(
        dashboard_service,
        historical,
    )


# ---------------------------------------------------------------------------
# Findings / AI
# ---------------------------------------------------------------------------

def get_findings_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FindingsService:
    return FindingsService(
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        RepositoryRepository(db),
    )


def get_finding_ai_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FindingAIService:
    return FindingAIService(
        FindingRepository(db),
    )


def get_ai_assistant_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AIAssistantService:
    return AIAssistantService(
        RepositoryRepository(db),
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
    )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def get_report_generation_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> ReportGenerationService:
    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)

    github_service = GitHubIntegrationService(
        IntegrationRepository(db),
        repo_repo,
    )

    repository_service = RepositoryService(
        repo_repo,
        pr_repo,
        github_service,
        AnalysisRunRepository(db),
    )

    findings_service = FindingsService(
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        repo_repo,
    )

    intelligence_service = RepositoryIntelligenceService(
        repo_repo,
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        pr_repo,
        IntegrationRepository(db),
        repository_service,
        findings_service,
    )

    return ReportGenerationService(
        repo_repo,
        FindingRepository(db),
        DependencyRepository(db),
        AnalysisRunRepository(db),
        AnalysisSnapshotRepository(db),
        intelligence_service,
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def get_notification_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> NotificationService:
    return NotificationService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
    )


def get_notification_event_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> NotificationEventService:
    return NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
        PullRequestRepository(db),
        AnalysisSnapshotRepository(db),
    )


# ---------------------------------------------------------------------------
# Audit / Organization / Members
# ---------------------------------------------------------------------------

def get_audit_log_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AuditLogService:
    return AuditLogService(
        AuditLogRepository(db),
        UserRepository(db),
    )


def get_organization_settings_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    audit: Annotated[
        AuditLogService,
        Depends(get_audit_log_service),
    ],
) -> OrganizationSettingsService:
    return OrganizationSettingsService(
        OrganizationRepository(db),
        MembershipRepository(db),
        RepositoryRepository(db),
        audit,
    )


def get_members_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    audit: Annotated[
        AuditLogService,
        Depends(get_audit_log_service),
    ],
    notification_events: Annotated[
        NotificationEventService,
        Depends(get_notification_event_service),
    ],
) -> MembersService:
    return MembersService(
        MembershipRepository(db),
        UserRepository(db),
        InvitationRepository(db),
        audit,
        notification_events,
    )


# ---------------------------------------------------------------------------
# Authentication cookies
# ---------------------------------------------------------------------------

def set_auth_cookies(
    response: Response,
    user_id: str,
) -> None:
    settings = get_settings()

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    # IMPORTANT:
    # Use cookie_secure from configuration.
    #
    # Local development:
    #   COOKIE_SECURE=false
    #   http://localhost:5173
    #
    # Production:
    #   COOKIE_SECURE=true
    #   HTTPS
    #
    cookie_secure = settings.cookie_secure

    response.set_cookie(
        key=settings.session_cookie_name,
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_max_age_seconds,
        path="/",
    )

    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_max_age_seconds,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )

    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/",
    )


# ---------------------------------------------------------------------------
# Current user / session
# ---------------------------------------------------------------------------

async def get_current_user_id_from_cookie(
    request: Request,
) -> str:
    settings = get_settings()

    session = request.cookies.get(
        settings.session_cookie_name,
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    user_id = decode_access_token(session)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    return user_id


async def get_current_user(
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
    user_id: Annotated[
        str,
        Depends(get_current_user_id_from_cookie),
    ],
) -> UserResponse:
    user = await auth_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return user


async def get_current_session(
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
    user_id: Annotated[
        str,
        Depends(get_current_user_id_from_cookie),
    ],
) -> SessionResponse:
    try:
        return await auth_service.get_session(user_id)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        ) from None


# ---------------------------------------------------------------------------
# Membership / authorization
# ---------------------------------------------------------------------------

async def get_membership_context(
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
    user_id: Annotated[
        str,
        Depends(get_current_user_id_from_cookie),
    ],
) -> MembershipContext:
    organization_id = await auth_service.get_organization_id(user_id)

    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No workspace found.",
        )

    membership = await auth_service.get_membership(
        user_id,
        organization_id,
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership not found.",
        )

    return MembershipContext(
        user_id=user_id,
        organization_id=organization_id,
        role=MembershipRole(membership["role"]),
        membership_id=membership["id"],
    )


def require_min_role(
    minimum_role: MembershipRole,
) -> Callable[..., MembershipContext]:

    async def _dependency(
        context: Annotated[
            MembershipContext,
            Depends(get_membership_context),
        ],
    ) -> MembershipContext:

        if ROLE_RANK[context.role] < ROLE_RANK[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return context

    return _dependency


RequireViewer = Annotated[
    MembershipContext,
    Depends(require_min_role(MembershipRole.VIEWER)),
]

RequireMember = Annotated[
    MembershipContext,
    Depends(require_min_role(MembershipRole.MEMBER)),
]

RequireAdmin = Annotated[
    MembershipContext,
    Depends(require_min_role(MembershipRole.ADMIN)),
]

RequireOwner = Annotated[
    MembershipContext,
    Depends(require_min_role(MembershipRole.OWNER)),
]


def require_permission(
    permission: Permission,
) -> Callable[..., MembershipContext]:

    async def _dependency(
        context: Annotated[
            MembershipContext,
            Depends(get_membership_context),
        ],
    ) -> MembershipContext:

        if not can(context.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return context

    return _dependency


async def get_current_organization_id(
    context: Annotated[
        MembershipContext,
        Depends(get_membership_context),
    ],
) -> str:
    return context.organization_id


# ---------------------------------------------------------------------------
# Backwards-compatible aliases used by auth routes
# ---------------------------------------------------------------------------

set_session_cookie = set_auth_cookies
clear_session_cookie = clear_auth_cookies

