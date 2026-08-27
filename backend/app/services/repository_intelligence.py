from typing import Any

from app.lib.dashboard_helpers import format_datetime, pr_risk_level, pr_verdict
from app.lib.metric_definitions import METRIC_DEFINITIONS, TRENDS_BASELINE_MESSAGE
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.integrations import IntegrationRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.findings import (
    DependencyResponse,
    DependencySummary,
    QualityFindingResponse,
    QualitySummary,
    SecurityFindingResponse,
    SecuritySummary,
    SeverityCounts,
)
from app.schemas.pagination import PaginatedResponse
from app.schemas.repository import (
    AnalysisRunDetailResponse,
    AnalysisRunResponse,
    RepositoryPullRequestResponse,
    RepositoryResponse,
)
from app.schemas.repository_intelligence import (
    HealthHistoryPoint,
    HealthHistoryResponse,
    RepositoryConnectionInfo,
    RepositoryHealthBreakdown,
    RepositoryIntelligenceResponse,
    RepositoryRecommendedAction,
)
from app.services.findings import FindingsService
from app.services.repositories import RepositoryService
from app.services.risk_engine import compute_risk_metrics


def _dependency_score_from_counts(counts: dict[str, int]) -> float:
    vulnerable = counts.get("vulnerable", 0) + counts.get("critical", 0)
    return max(0.0, 100.0 - (vulnerable * 10))


def _worst_dependency_status(counts: dict[str, int]) -> str | None:
    if counts.get("critical", 0) > 0:
        return "critical"
    if counts.get("vulnerable", 0) > 0:
        return "vulnerable"
    if counts.get("outdated", 0) > 0:
        return "outdated"
    if counts.get("healthy", 0) > 0:
        return "healthy"
    # BUG FIX: previously fell back to "healthy" whenever
    # counts["total"] > 0, which wrongly labeled dependencies from
    # inventory-only ecosystems (Go/Rust/PHP/Ruby - status "unknown",
    # never vulnerability-scanned) as verified-healthy. "unknown" is
    # reported honestly instead of being folded into "healthy".
    if counts.get("unknown", 0) > 0:
        return "unknown"
    return None


class RepositoryIntelligenceService:
    def __init__(
        self,
        repositories: RepositoryRepository,
        findings: FindingRepository,
        dependencies: DependencyRepository,
        analysis_runs: AnalysisRunRepository,
        pull_requests: PullRequestRepository,
        integrations: IntegrationRepository,
        repository_service: RepositoryService,
        findings_service: FindingsService,
    ) -> None:
        self._repositories = repositories
        self._findings = findings
        self._dependencies = dependencies
        self._analysis_runs = analysis_runs
        self._pull_requests = pull_requests
        self._integrations = integrations
        self._repository_service = repository_service
        self._findings_service = findings_service

    async def _ensure_repository(
        self,
        repository_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        return await self._repositories.get_by_id(
            repository_id,
            organization_id,
        )

    def _to_analysis_run(
        self,
        doc: dict[str, Any],
    ) -> AnalysisRunResponse:
        return self._repository_service.to_analysis_run_response(doc)

    def _to_analysis_run_detail(
        self,
        doc: dict[str, Any],
    ) -> AnalysisRunDetailResponse:
        base = self._to_analysis_run(doc)

        return AnalysisRunDetailResponse(
            **base.model_dump(),
            analyzer_summary=doc.get("analyzer_summary"),
            health_snapshot=doc.get("health_snapshot"),
        )

    async def get_intelligence(
        self,
        repository_id: str,
        organization_id: str,
    ) -> RepositoryIntelligenceResponse | None:
        repo_doc = await self._ensure_repository(
            repository_id,
            organization_id,
        )

        if not repo_doc:
            return None

        repository = self._repository_service.to_repository_response(
            repo_doc
        )

        has_completed = repo_doc.get("analysis_status") == "complete"

        latest_run_doc = (
            await self._analysis_runs.latest_for_repository(
                repository_id,
                organization_id,
            )
        )

        latest_analysis = (
            self._to_analysis_run(latest_run_doc)
            if latest_run_doc
            else None
        )

        security_categories = [
            "security",
            "secret",
            "dependency",
        ]

        security_counts = (
            await self._findings.count_by_severity_for_repository(
                repository_id,
                organization_id,
                categories=security_categories,
            )
        )

        quality_findings = await self._findings.list_by_repository(
            repository_id,
            organization_id,
            categories=["quality"],
        )

        dep_counts = (
            await self._dependencies.summary_counts_for_repository(
                repository_id,
                organization_id,
            )
        )

        dep_score = repo_doc.get("dependency_score")

        if dep_score is None and dep_counts.get("total", 0) > 0:
            dep_score = _dependency_score_from_counts(dep_counts)

        pr_avg = await self._pull_requests.average_risk_score(
            organization_id,
            repository_id=repository_id,
        )

        connection = await self._connection_info(
            organization_id,
            repo_doc,
        )

        security_summary = SecuritySummary(
            score=repo_doc.get("security_score"),
            severity_counts=SeverityCounts(**security_counts),
            has_analysis_data=has_completed,
        )

        quality_metrics = (
            compute_risk_metrics(quality_findings)
            if quality_findings
            else None
        )

        quality_summary = QualitySummary(
            score=repo_doc.get("code_quality_score"),
            maintainability_score=repo_doc.get("code_quality_score"),
            has_analysis_data=has_completed,
        )

        if quality_metrics:
            quality_summary = QualitySummary(
                score=quality_metrics.code_quality_score,
                maintainability_score=quality_metrics.code_quality_score,
                has_analysis_data=has_completed,
            )

        vulnerable = (
            dep_counts.get("vulnerable", 0)
            + dep_counts.get("critical", 0)
        )

        dependency_summary = DependencySummary(
            health_score=dep_score,
            total_packages=dep_counts.get("total", 0),
            outdated_count=dep_counts.get("outdated", 0),
            vulnerable_count=vulnerable,
            has_analysis_data=(
                has_completed
                and dep_counts.get("total", 0) > 0
            ),
        )

        health = RepositoryHealthBreakdown(
            health_score=repo_doc.get("health_score"),
            security_score=repo_doc.get("security_score"),
            code_quality_score=repo_doc.get("code_quality_score"),
            dependency_score=dep_score,
            pr_risk_average=pr_avg,
            risk_level=repo_doc.get("risk_level"),
            has_completed_analysis=has_completed,
            health_definition=METRIC_DEFINITIONS["engineering_health"],
            security_definition=METRIC_DEFINITIONS["security"],
            quality_definition=METRIC_DEFINITIONS["code_quality"],
            dependency_definition=METRIC_DEFINITIONS["dependencies"],
            pr_risk_definition=METRIC_DEFINITIONS["pull_request_risk"],
        )

        actions = self._recommended_actions(
            repository,
            repo_doc,
            security_counts,
            connection,
        )

        return RepositoryIntelligenceResponse(
            repository=repository,
            health=health,
            connection=connection,
            latest_analysis=latest_analysis,
            security_summary=security_summary,
            quality_summary=quality_summary,
            dependency_summary=dependency_summary,
            recommended_actions=actions,
        )

    async def _connection_info(
        self,
        organization_id: str,
        repo_doc: dict[str, Any],
    ) -> RepositoryConnectionInfo:
        integration = (
            await self._integrations.get_github_by_organization(
                organization_id
            )
        )

        if not integration:
            return RepositoryConnectionInfo(
                github_status="disconnected",
                can_analyze=False,
                analyze_blocked_reason=(
                    "Connect GitHub in workspace settings "
                    "to analyze repositories."
                ),
            )

        status = integration.get("status", "connected")

        github_status = (
            "connected"
            if status == "connected"
            else "error"
            if status == "error"
            else "disconnected"
        )

        return RepositoryConnectionInfo(
            github_status=github_status,
            github_login=integration.get("github_login"),
            last_synchronized_at=format_datetime(
                repo_doc.get("updated_at")
            ),
            can_analyze=github_status == "connected",
            analyze_blocked_reason=(
                None
                if github_status == "connected"
                else "GitHub connection is not active."
            ),
        )

    def _recommended_actions(
        self,
        repository: RepositoryResponse,
        repo_doc: dict[str, Any],
        security_counts: dict[str, int],
        connection: RepositoryConnectionInfo,
    ) -> list[RepositoryRecommendedAction]:
        actions: list[RepositoryRecommendedAction] = []

        if repo_doc.get("analysis_status") in {
            "not_started",
            "failed",
        }:
            actions.append(
                RepositoryRecommendedAction(
                    id="analyze",
                    label="Run repository analysis",
                    description=(
                        "Analyze this repository to compute "
                        "health, security, and quality scores."
                    ),
                    priority="high",
                )
            )

        if security_counts.get("critical", 0) > 0:
            actions.append(
                RepositoryRecommendedAction(
                    id="critical-findings",
                    label="Review critical security findings",
                    description=(
                        f"{security_counts['critical']} critical "
                        "finding(s) require immediate attention."
                    ),
                    priority="high",
                )
            )

        if not connection.can_analyze:
            actions.append(
                RepositoryRecommendedAction(
                    id="connect-github",
                    label="Restore GitHub connection",
                    description=(
                        connection.analyze_blocked_reason
                        or "GitHub must be connected to analyze."
                    ),
                    priority="medium",
                )
            )

        if (
            repository.open_pull_requests > 0
            and repo_doc.get("analysis_status") == "complete"
        ):
            actions.append(
                RepositoryRecommendedAction(
                    id="review-prs",
                    label="Review open pull requests",
                    description=(
                        f"{repository.open_pull_requests} open "
                        "pull request(s) may need risk review."
                    ),
                    priority="medium",
                )
            )

        return actions

    async def get_analysis_run_detail(
        self,
        repository_id: str,
        analysis_id: str,
        organization_id: str,
    ) -> AnalysisRunDetailResponse | None:
        """
        Return detailed information for a specific analysis run.

        The analysis must:
        1. Belong to the requested organization.
        2. Belong to the requested repository.

        For the latest completed analysis, also include
        findings grouped by category.
        """
        if not await self._ensure_repository(
            repository_id,
            organization_id,
        ):
            return None

        doc = await self._analysis_runs.get_by_id(
            analysis_id,
            organization_id,
        )

        if not doc or doc.get("repository_id") != repository_id:
            return None

        detail = self._to_analysis_run_detail(doc)

        if doc.get("status") == "complete":
            latest = (
                await self._analysis_runs.latest_for_repository(
                    repository_id,
                    organization_id,
                )
            )

            if latest and latest.get("id") == analysis_id:
                findings = await self._findings.list_by_repository(
                    repository_id,
                    organization_id,
                )

                by_category: dict[str, int] = {}

                for finding in findings:
                    category = str(
                        finding.get("category", "unknown")
                    )

                    by_category[category] = (
                        by_category.get(category, 0) + 1
                    )

                detail.findings_by_category = by_category

        return detail

    async def list_health_history(
        self,
        repository_id: str,
        organization_id: str,
    ) -> HealthHistoryResponse | None:
        if not await self._ensure_repository(
            repository_id,
            organization_id,
        ):
            return None

        runs = (
            await self._analysis_runs.list_completed_health_history(
                repository_id,
                organization_id,
            )
        )

        points: list[HealthHistoryPoint] = []

        for run in reversed(runs):
            snapshot = run.get("health_snapshot")

            if not isinstance(snapshot, dict):
                continue

            severity = snapshot.get("severity_counts")

            points.append(
                HealthHistoryPoint(
                    analysis_id=run["id"],
                    recorded_at=format_datetime(
                        run.get("completed_at")
                    ),
                    health_score=snapshot.get("health_score"),
                    security_score=snapshot.get("security_score"),
                    code_quality_score=snapshot.get(
                        "code_quality_score"
                    ),
                    dependency_score=snapshot.get(
                        "dependency_score"
                    ),
                    risk_level=snapshot.get("risk_level"),
                    severity_counts=(
                        SeverityCounts(**severity)
                        if isinstance(severity, dict)
                        else None
                    ),
                )
            )

        sufficient = len(points) >= 2

        return HealthHistoryResponse(
            points=points,
            has_sufficient_history=sufficient,
            message=(
                TRENDS_BASELINE_MESSAGE
                if not sufficient
                else "Health history from completed analyses."
            ),
        )

    async def list_findings_paginated(
        self,
        repository_id: str,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        category: str | None = None,
        severity: str | None = None,
    ) -> PaginatedResponse[
        SecurityFindingResponse | QualityFindingResponse
    ] | None:
        repo_doc = await self._ensure_repository(
            repository_id,
            organization_id,
        )

        if not repo_doc:
            return None

        categories: list[str] | None = None

        if category == "security":
            categories = [
                "security",
                "secret",
                "dependency",
            ]
        elif category == "quality":
            categories = ["quality"]

        skip = (page - 1) * page_size

        docs, total = (
            await self._findings.list_by_repository_paginated(
                repository_id,
                organization_id,
                categories=categories,
                severity=severity,
                skip=skip,
                limit=page_size,
            )
        )

        repo_names = {
            repository_id: (
                repo_doc.get("full_name")
                or repo_doc.get("name", "")
            )
        }

        items: list[
            SecurityFindingResponse | QualityFindingResponse
        ] = []

        for doc in docs:
            if doc.get("category") == "quality":
                items.append(
                    self._findings_service._to_quality_finding(
                        doc,
                        repo_names,
                    )
                )
            else:
                items.append(
                    self._findings_service._to_security_finding(
                        doc,
                        repo_names,
                    )
                )

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def list_dependencies_paginated(
        self,
        repository_id: str,
        organization_id: str,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[DependencyResponse] | None:
        repo_doc = await self._ensure_repository(
            repository_id,
            organization_id,
        )

        if not repo_doc:
            return None

        skip = (page - 1) * page_size

        docs, total = (
            await self._dependencies.list_by_repository_paginated(
                repository_id,
                organization_id,
                skip=skip,
                limit=page_size,
            )
        )

        repo_names = {
            repository_id: (
                repo_doc.get("full_name")
                or repo_doc.get("name", "")
            )
        }

        items = [
            self._findings_service._to_dependency(
                doc,
                repo_names,
            )
            for doc in docs
        ]

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def list_pull_requests_paginated(
        self,
        repository_id: str,
        organization_id: str,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[RepositoryPullRequestResponse] | None:
        if not await self._ensure_repository(
            repository_id,
            organization_id,
        ):
            return None

        skip = (page - 1) * page_size

        docs, total = (
            await self._pull_requests.list_by_repository_paginated(
                repository_id=repository_id,
                organization_id=organization_id,
                skip=skip,
                limit=page_size,
            )
        )

        items: list[RepositoryPullRequestResponse] = []

        for doc in docs:
            base = (
                self._repository_service.to_pull_request_response(
                    doc
                )
            )

            verdict, label, reason = pr_verdict(
                doc.get("risk_score")
            )

            items.append(
                RepositoryPullRequestResponse(
                    **base.model_dump(),
                    verdict=verdict,
                    verdict_label=label,
                    verdict_reason=reason,
                    risk_level=pr_risk_level(
                        doc.get("risk_score")
                    ),
                    updated_at=format_datetime(
                        doc.get("updated_at")
                    ),
                )
            )

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )