from typing import Literal

from app.schemas.common import APIModel

NotificationType = Literal[
    "security.critical_finding",
    "dependency.critical_vulnerability",
    "pr.high_risk",
    "quality.regression",
    "health.regression",
    "analysis.completed",
    "analysis.failed",
    "analysis.stale",
    "workspace.member_invited",
    "workspace.member_removed",
    "workspace.role_changed",
    "workspace.invitation_revoked",
    "integration.connected",
    "integration.disconnected",
]

NotificationSeverity = Literal["critical", "high", "warning", "info"]

NotificationSortField = Literal["created_at", "severity"]


class NotificationResponse(APIModel):
    id: str
    type: NotificationType
    severity: NotificationSeverity
    title: str
    body: str
    href: str
    repository_id: str | None = None
    repository_name: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    read: bool
    created_at: str | None = None


class UnreadCountResponse(APIModel):
    count: int


class NotificationPreferencesResponse(APIModel):
    security_alerts: bool = True
    dependency_alerts: bool = True
    pr_risk_alerts: bool = True
    analysis_alerts: bool = True
    regression_alerts: bool = True
    workspace_alerts: bool = True


class NotificationPreferencesUpdate(APIModel):
    security_alerts: bool | None = None
    dependency_alerts: bool | None = None
    pr_risk_alerts: bool | None = None
    analysis_alerts: bool | None = None
    regression_alerts: bool | None = None
    workspace_alerts: bool | None = None
