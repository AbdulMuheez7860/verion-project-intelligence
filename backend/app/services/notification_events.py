from typing import Any

from app.lib.historical_helpers import compare_metric, is_material_regression
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.memberships import MembershipRepository
from app.repositories.notification_preferences import NotificationPreferencesRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.pull_requests import PullRequestRepository
from app.schemas.auth import MembershipRole
from app.schemas.notifications import NotificationSeverity, NotificationType
from app.services.notifications import NotificationService

EVENT_PREFERENCE_KEY: dict[NotificationType, str] = {
    "security.critical_finding": "security_alerts",
    "dependency.critical_vulnerability": "dependency_alerts",
    "pr.high_risk": "pr_risk_alerts",
    "quality.regression": "regression_alerts",
    "health.regression": "regression_alerts",
    "analysis.completed": "analysis_alerts",
    "analysis.failed": "analysis_alerts",
    "analysis.stale": "analysis_alerts",
    "workspace.member_invited": "workspace_alerts",
    "workspace.member_removed": "workspace_alerts",
    "workspace.role_changed": "workspace_alerts",
    "workspace.invitation_revoked": "workspace_alerts",
    "integration.connected": "workspace_alerts",
    "integration.disconnected": "workspace_alerts",
}

WORKSPACE_EVENT_TYPES = frozenset({
    "workspace.member_invited",
    "workspace.member_removed",
    "workspace.role_changed",
    "workspace.invitation_revoked",
    "integration.connected",
    "integration.disconnected",
})

ADMIN_ROLES = {MembershipRole.ADMIN.value, MembershipRole.OWNER.value}

STALE_ANALYSIS_DAYS = 7


class NotificationEventService:
    def __init__(
        self,
        notifications: NotificationRepository,
        preferences: NotificationPreferencesRepository,
        memberships: MembershipRepository,
        pull_requests: PullRequestRepository | None = None,
        snapshots: AnalysisSnapshotRepository | None = None,
    ) -> None:
        self._notifications = notifications
        self._preferences = preferences
        self._memberships = memberships
        self._pull_requests = pull_requests
        self._snapshots = snapshots
        self._service = NotificationService(notifications, preferences)

    async def _eligible_user_ids(
        self,
        *,
        organization_id: str,
        notification_type: NotificationType,
        workspace_only: bool = False,
    ) -> list[tuple[str, str]]:
        preference_key = EVENT_PREFERENCE_KEY[notification_type]
        members, _ = await self._memberships.list_by_organization(organization_id, limit=500)
        eligible: list[tuple[str, str]] = []
        for member in members:
            user_id = str(member.get("user_id", ""))
            role = str(member.get("role", "viewer"))
            if not user_id:
                continue
            if workspace_only and role not in ADMIN_ROLES:
                continue
            prefs = await self._preferences.get_or_create(
                organization_id=organization_id,
                user_id=user_id,
            )
            if prefs.get(preference_key, True):
                eligible.append((user_id, role))
        return eligible

    async def emit(
        self,
        *,
        organization_id: str,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        body: str,
        href: str,
        idempotency_key: str,
        repository_id: str | None = None,
        repository_name: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        workspace_only: bool | None = None,
    ) -> int:
        workspace_event = workspace_only if workspace_only is not None else notification_type in WORKSPACE_EVENT_TYPES
        recipients = await self._eligible_user_ids(
            organization_id=organization_id,
            notification_type=notification_type,
            workspace_only=workspace_event,
        )
        created = 0
        for user_id, _role in recipients:
            doc = await self._service.create_notification(
                organization_id=organization_id,
                user_id=user_id,
                notification_type=notification_type,
                severity=severity,
                title=title,
                body=body,
                href=href,
                idempotency_key=f"{idempotency_key}:{user_id}",
                repository_id=repository_id,
                repository_name=repository_name,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
            )
            if doc:
                created += 1
        return created

    async def emit_analysis_completed(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        analysis_run_id: str,
        finding_count: int,
    ) -> int:
        return await self.emit(
            organization_id=organization_id,
            notification_type="analysis.completed",
            severity="info",
            title="Analysis completed",
            body=f"{repository_name} analysis finished with {finding_count} findings.",
            href=f"/app/analysis-runs/{analysis_run_id}",
            idempotency_key=f"analysis.completed:{analysis_run_id}",
            repository_id=repository_id,
            repository_name=repository_name,
            resource_type="analysis_run",
            resource_id=analysis_run_id,
        )

    async def emit_analysis_failed(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        analysis_run_id: str,
        error: str,
    ) -> int:
        return await self.emit(
            organization_id=organization_id,
            notification_type="analysis.failed",
            severity="critical",
            title="Analysis failed",
            body=f"{repository_name} analysis failed. {error[:200]}",
            href=f"/app/analysis-runs/{analysis_run_id}",
            idempotency_key=f"analysis.failed:{analysis_run_id}",
            repository_id=repository_id,
            repository_name=repository_name,
            resource_type="analysis_run",
            resource_id=analysis_run_id,
            metadata={"error": error[:500]},
        )

    async def emit_critical_security(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        critical_count: int,
        analysis_run_id: str,
    ) -> int:
        if critical_count <= 0:
            return 0
        label = "finding" if critical_count == 1 else "findings"
        return await self.emit(
            organization_id=organization_id,
            notification_type="security.critical_finding",
            severity="critical",
            title="Critical security finding detected",
            body=f"{repository_name} has {critical_count} critical security {label}.",
            href="/app/security",
            idempotency_key=f"security.critical:{analysis_run_id}",
            repository_id=repository_id,
            repository_name=repository_name,
            resource_type="repository",
            resource_id=repository_id,
            metadata={"critical_count": critical_count},
        )

    async def emit_critical_dependency(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        critical_count: int,
        analysis_run_id: str,
    ) -> int:
        if critical_count <= 0:
            return 0
        label = "vulnerability" if critical_count == 1 else "vulnerabilities"
        return await self.emit(
            organization_id=organization_id,
            notification_type="dependency.critical_vulnerability",
            severity="critical",
            title="Critical dependency vulnerability",
            body=f"{repository_name} has {critical_count} critical dependency {label}.",
            href="/app/dependencies",
            idempotency_key=f"dependency.critical:{analysis_run_id}",
            repository_id=repository_id,
            repository_name=repository_name,
            resource_type="repository",
            resource_id=repository_id,
            metadata={"critical_count": critical_count},
        )

    async def emit_high_risk_prs(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        analysis_run_id: str,
    ) -> None:
        if not self._pull_requests:
            return
        pulls, _ = await self._pull_requests.list_by_repository_paginated(
            repository_id=repository_id,
            organization_id=organization_id,
            skip=0,
            limit=50,
        )
        for pull in pulls:
            risk_score = pull.get("risk_score")
            if not isinstance(risk_score, int) or risk_score < 50:
                continue
            pr_id = str(pull.get("id", ""))
            number = pull.get("number")
            title = pull.get("title", "Pull request")
            await self.emit(
                organization_id=organization_id,
                notification_type="pr.high_risk",
                severity="high" if risk_score < 70 else "critical",
                title="High-risk pull request",
                body=f"#{number} {title} in {repository_name} scored {risk_score}/100.",
                href=f"/app/pull-requests/{pr_id}",
                idempotency_key=f"pr.high_risk:{analysis_run_id}:{pr_id}",
                repository_id=repository_id,
                repository_name=repository_name,
                resource_type="pull_request",
                resource_id=pr_id,
                metadata={"risk_score": risk_score, "pr_number": number},
            )

    async def emit_regressions(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        analysis_run_id: str,
    ) -> None:
        if not self._snapshots:
            return
        latest, previous = await self._snapshots.get_snapshot_comparison(
            organization_id,
            repository_id,
        )
        if not latest or not previous:
            return

        checks: list[tuple[str, NotificationType, str]] = [
            ("health_score", "health.regression", "Health regression detected"),
            ("quality_score", "quality.regression", "Quality regression detected"),
        ]
        for metric, event_type, title in checks:
            current = latest.get(metric)
            previous_val = previous.get(metric)
            change = compare_metric(
                metric=metric,
                current=current,
                previous=previous_val,
                label=metric.replace("_", " ").title(),
            )
            if not is_material_regression(metric, change.get("delta")):
                continue
            await self.emit(
                organization_id=organization_id,
                notification_type=event_type,
                severity="warning",
                title=title,
                body=f"{repository_name}: {change.get('interpretation', 'Material regression detected.')}",
                href=f"/app/repositories/{repository_id}",
                idempotency_key=f"{event_type}:{analysis_run_id}:{metric}",
                repository_id=repository_id,
                repository_name=repository_name,
                resource_type="repository",
                resource_id=repository_id,
                metadata={"metric": metric, "delta": change.get("delta")},
            )

    async def emit_analysis_stale(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        days_since_analysis: int,
    ) -> None:
        await self.emit(
            organization_id=organization_id,
            notification_type="analysis.stale",
            severity="warning",
            title="Analysis stale",
            body=f"{repository_name} has not been analyzed in {days_since_analysis} days.",
            href=f"/app/repositories/{repository_id}",
            idempotency_key=f"analysis.stale:{repository_id}:{days_since_analysis // STALE_ANALYSIS_DAYS}",
            repository_id=repository_id,
            repository_name=repository_name,
            resource_type="repository",
            resource_id=repository_id,
            metadata={"days_since_analysis": days_since_analysis},
        )

    async def emit_workspace_event(
        self,
        *,
        organization_id: str,
        notification_type: NotificationType,
        title: str,
        body: str,
        href: str,
        idempotency_key: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.emit(
            organization_id=organization_id,
            notification_type=notification_type,
            severity="info",
            title=title,
            body=body,
            href=href,
            idempotency_key=idempotency_key,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            workspace_only=True,
        )
