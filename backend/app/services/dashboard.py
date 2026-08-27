from datetime import UTC, datetime

from app.lib.dashboard_helpers import (
    duration_seconds,
    format_datetime,
    health_level_from_score,
    pr_risk_level,
    pr_verdict,
)
from app.lib.metric_definitions import (
    METRIC_DEFINITIONS,
    TRENDS_BASELINE_MESSAGE,
)
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.dashboard import (
    AnalysisActivityItem,
    AttentionItem,
    DashboardMetrics,
    DashboardResponse,
    DashboardSummaryResponse,
    EngineeringHealth,
    HealthDimension,
    HighRiskChange,
    OverviewMetric,
    PullRequestDashboardItem,
    PullRequestSection,
    RecommendedAction,
    RepositoryDashboardItem,
    RepositoryHealthItem,
    RiskDistribution,
    RiskDistributionBucket,
    SecurityOverview,
    TrendsSection,
)
from app.schemas.findings import SeverityCounts
from app.services.repositories import RepositoryService


class DashboardService:
    def __init__(
        self,
        repositories: RepositoryRepository,
        pull_requests: PullRequestRepository,
        repository_service: RepositoryService,
        findings: FindingRepository,
        analysis_runs: AnalysisRunRepository,
        dependencies: DependencyRepository,
    ) -> None:
        self._repositories = repositories
        self._pull_requests = pull_requests
        self._repository_service = repository_service
        self._findings = findings
        self._analysis_runs = analysis_runs
        self._dependencies = dependencies

    async def get_dashboard(
        self,
        organization_id: str,
    ) -> DashboardResponse:
        summary = await self.get_dashboard_summary(organization_id)

        metrics = DashboardMetrics(
            has_analysis_data=summary.has_analysis_data,
            connected_repositories=next(
                (
                    int(item.value)
                    for item in summary.overview
                    if item.key == "repositories"
                    and item.value is not None
                ),
                0,
            ),
            repository_health=summary.health.score,
            security_score=next(
                (
                    dimension.score
                    for dimension in summary.health.dimensions
                    if dimension.key == "security"
                ),
                None,
            ),
            code_quality_score=next(
                (
                    dimension.score
                    for dimension in summary.health.dimensions
                    if dimension.key == "code_quality"
                ),
                None,
            ),
            pr_risk=next(
                (
                    dimension.score
                    for dimension in summary.health.dimensions
                    if dimension.key == "pull_request_risk"
                ),
                None,
            ),
        )

        high_risk_changes = [
            HighRiskChange(
                repository_name=item.repository_name,
                pull_request_id=item.id,
                pull_request_title=item.title,
                risk_score=item.risk_score or 0,
                findings_count=item.issues_count,
            )
            for item in summary.pull_requests.high_risk
        ]

        pr_docs = await self._pull_requests.list_by_organization(
            organization_id,
            limit=5,
        )

        repository_health_items = [
            RepositoryHealthItem(
                id=item.id,
                name=item.name,
                health_score=item.health_score,
            )
            for item in summary.repositories
        ]

        return DashboardResponse(
            metrics=metrics,
            attention_items=summary.attention,
            recent_pull_requests=[
                self._repository_service.to_pull_request_response(doc)
                for doc in pr_docs
            ],
            repository_health_items=repository_health_items,
            high_risk_changes=high_risk_changes,
            security_severity_counts=summary.security.severity_counts,
        )

    async def get_dashboard_summary(
        self,
        organization_id: str,
    ) -> DashboardSummaryResponse:
        now = datetime.now(UTC)

        repo_count = await self._repositories.count_by_organization(
            organization_id
        )

        has_data = (
            await self._analysis_runs.has_completed_for_organization(
                organization_id
            )
        )

        has_active = (
            await self._analysis_runs.has_active_for_organization(
                organization_id
            )
        )

        completed_runs = (
            await self._analysis_runs.count_completed_by_organization(
                organization_id
            )
        )

        repos = await self._repositories.list_by_organization(
            organization_id
        )

        repo_names = {
            repo["id"]: repo.get("full_name") or repo.get("name", "")
            for repo in repos
        }

        open_pr_count = (
            await self._pull_requests.count_open_by_organization(
                organization_id
            )
        )

        high_risk_pr_count = (
            await self._pull_requests.count_high_risk_open(
                organization_id
            )
        )

        security_severity_counts: SeverityCounts | None = None
        security_total = 0
        critical_count = 0

        dependency_score: float | None = None
        avg_health: float | None = None
        avg_security: float | None = None
        avg_quality: float | None = None
        avg_pr_risk: float | None = None

        repos_requiring_attention = 0
        health_factors: list[str] = []

        # ---------------------------------------------------------
        # Analysis-derived metrics
        # ---------------------------------------------------------
        if has_data:
            analyzed = [
                repo
                for repo in repos
                if repo.get("health_score") is not None
            ]

            if analyzed:
                health_values = [
                    float(repo["health_score"])
                    for repo in analyzed
                ]

                avg_health = round(
                    sum(health_values) / len(health_values),
                    1,
                )

                security_values = [
                    float(repo["security_score"])
                    for repo in analyzed
                    if repo.get("security_score") is not None
                ]

                if security_values:
                    avg_security = round(
                        sum(security_values) / len(security_values),
                        1,
                    )

                quality_values = [
                    float(repo["code_quality_score"])
                    for repo in analyzed
                    if repo.get("code_quality_score") is not None
                ]

                if quality_values:
                    avg_quality = round(
                        sum(quality_values) / len(quality_values),
                        1,
                    )

            # Security / secret / dependency findings
            severity_map = await self._findings.count_by_severity(
                organization_id,
                ["security", "secret", "dependency"],
            )

            security_severity_counts = SeverityCounts(**severity_map)

            security_total = sum(severity_map.values())

            critical_count = severity_map.get("critical", 0)

            # Dependency health
            dep_counts = await self._dependencies.summary_counts(
                organization_id
            )

            vulnerable = (
                dep_counts.get("vulnerable", 0)
                + dep_counts.get("critical", 0)
            )

            dependency_total = dep_counts.get("total", 0)

            if dependency_total > 0:
                dependency_score = round(
                    max(0.0, 100.0 - (vulnerable * 10)),
                    1,
                )

            # Pull request risk
            avg_pr_risk_value = (
                await self._pull_requests.average_risk_score(
                    organization_id
                )
            )

            if avg_pr_risk_value is not None:
                avg_pr_risk = round(
                    float(avg_pr_risk_value),
                    1,
                )

            # Health factors
            if critical_count:
                health_factors.append(
                    f"{critical_count} critical security finding"
                    f"{'s' if critical_count != 1 else ''} open"
                )

            if high_risk_pr_count:
                health_factors.append(
                    f"{high_risk_pr_count} high-risk pull request"
                    f"{'s' if high_risk_pr_count != 1 else ''} open"
                )

        # ---------------------------------------------------------
        # Repository attention
        # ---------------------------------------------------------
        for repo in repos:
            status = str(
                repo.get("analysis_status", "not_started")
            )

            risk = repo.get("risk_level")
            health = repo.get("health_score")

            if (
                status in {"failed", "not_started"}
                or risk in {"critical", "high"}
                or (
                    isinstance(health, (int, float))
                    and health < 50
                )
            ):
                repos_requiring_attention += 1

        # ---------------------------------------------------------
        # Overview
        # ---------------------------------------------------------
        overview = self._build_overview(
            avg_health=avg_health,
            repo_count=repo_count,
            open_pr_count=open_pr_count,
            security_total=security_total,
            critical_count=critical_count,
            high_risk_pr_count=high_risk_pr_count,
            repos_requiring_attention=repos_requiring_attention,
            has_data=has_data,
        )

        # ---------------------------------------------------------
        # Engineering health
        # ---------------------------------------------------------
        health = EngineeringHealth(
            score=avg_health,
            level=(
                health_level_from_score(avg_health)
                if has_data and avg_health is not None
                else "unavailable"
            ),
            definition=METRIC_DEFINITIONS["engineering_health"],
            dimensions=[
                HealthDimension(
                    key="repository_health",
                    label="Repository health",
                    score=avg_health,
                    definition=METRIC_DEFINITIONS[
                        "repository_health"
                    ],
                ),
                HealthDimension(
                    key="security",
                    label="Security",
                    score=avg_security,
                    definition=METRIC_DEFINITIONS["security"],
                ),
                HealthDimension(
                    key="code_quality",
                    label="Code quality",
                    score=avg_quality,
                    definition=METRIC_DEFINITIONS[
                        "code_quality"
                    ],
                ),
                HealthDimension(
                    key="dependencies",
                    label="Dependencies",
                    score=dependency_score,
                    definition=METRIC_DEFINITIONS[
                        "dependencies"
                    ],
                ),
                HealthDimension(
                    key="pull_request_risk",
                    label="Pull request risk",
                    score=avg_pr_risk,
                    definition=METRIC_DEFINITIONS[
                        "pull_request_risk"
                    ],
                ),
            ],
            factors=health_factors,
        )

        # ---------------------------------------------------------
        # Dashboard sections
        # ---------------------------------------------------------
        attention = await self._build_attention_items(
            organization_id,
            repos,
            repo_names,
            has_data,
        )

        repository_items = self._build_repository_items(repos)

        pull_request_section = (
            await self._build_pull_request_section(
                organization_id
            )
        )

        analysis_activity = await self._build_analysis_activity(
            organization_id,
            repo_names,
        )

        risk_distribution = self._build_risk_distribution(
            security_severity_counts,
            has_data,
        )

        trends = TrendsSection(
            available=False,
            message=(
                TRENDS_BASELINE_MESSAGE
                if has_data
                else (
                    "Connect repositories and complete analysis "
                    "to establish an engineering health baseline."
                )
            ),
            direction="unavailable",
            completed_analyses_count=completed_runs,
        )

        recommended_actions = self._build_recommended_actions(
            repo_count=repo_count,
            has_data=has_data,
            repos_requiring_attention=repos_requiring_attention,
            critical_count=critical_count,
            has_active=has_active,
        )

        return DashboardSummaryResponse(
            generated_at=now.isoformat(),
            has_active_analysis=has_active,
            has_analysis_data=has_data,
            overview=overview,
            health=health,
            attention=attention,
            repositories=repository_items,
            pull_requests=pull_request_section,
            security=SecurityOverview(
                severity_counts=security_severity_counts,
                total=security_total,
                has_data=has_data and security_total > 0,
            ),
            analysis_activity=analysis_activity,
            risk_distribution=risk_distribution,
            trends=trends,
            recommended_actions=recommended_actions,
        )

    # =============================================================
    # Overview
    # =============================================================

    def _build_overview(
        self,
        *,
        avg_health: float | None,
        repo_count: int,
        open_pr_count: int,
        security_total: int,
        critical_count: int,
        high_risk_pr_count: int,
        repos_requiring_attention: int,
        has_data: bool,
    ) -> list[OverviewMetric]:

        def status_for_health(
            score: float | None,
        ) -> str:
            if score is None:
                return "unavailable"

            if score >= 80:
                return "healthy"

            if score >= 60:
                return "warning"

            return "critical"

        return [
            OverviewMetric(
                key="engineering_health",
                label="Engineering health",
                value=avg_health if has_data else None,
                definition=METRIC_DEFINITIONS[
                    "engineering_health"
                ],
                href="/app/dashboard",
                status=(
                    status_for_health(avg_health)
                    if has_data
                    else "unavailable"
                ),
            ),
            OverviewMetric(
                key="repositories",
                label="Repositories",
                value=repo_count,
                definition=METRIC_DEFINITIONS["repositories"],
                href="/app/repositories",
                status="neutral",
            ),
            OverviewMetric(
                key="open_pull_requests",
                label="Open pull requests",
                value=open_pr_count,
                definition=METRIC_DEFINITIONS[
                    "open_pull_requests"
                ],
                href="/app/pull-requests",
                status="neutral",
            ),
            OverviewMetric(
                key="security_findings",
                label="Security findings",
                value=(
                    security_total
                    if has_data
                    else None
                ),
                definition=METRIC_DEFINITIONS[
                    "security_findings"
                ],
                href="/app/security",
                status=(
                    "warning"
                    if security_total
                    else (
                        "unavailable"
                        if not has_data
                        else "healthy"
                    )
                ),
            ),
            OverviewMetric(
                key="critical_findings",
                label="Critical findings",
                value=(
                    critical_count
                    if has_data
                    else None
                ),
                definition=METRIC_DEFINITIONS[
                    "critical_findings"
                ],
                href="/app/security",
                status=(
                    "critical"
                    if critical_count
                    else (
                        "unavailable"
                        if not has_data
                        else "healthy"
                    )
                ),
            ),
            OverviewMetric(
                key="high_risk_prs",
                label="High-risk PRs",
                value=(
                    high_risk_pr_count
                    if has_data
                    else None
                ),
                definition=METRIC_DEFINITIONS[
                    "high_risk_prs"
                ],
                href="/app/pull-requests",
                status=(
                    "critical"
                    if high_risk_pr_count
                    else (
                        "unavailable"
                        if not has_data
                        else "healthy"
                    )
                ),
            ),
            OverviewMetric(
                key="repositories_requiring_attention",
                label="Repos requiring attention",
                value=(
                    repos_requiring_attention
                    if repo_count
                    else 0
                ),
                definition=METRIC_DEFINITIONS[
                    "repositories_requiring_attention"
                ],
                href="/app/repositories",
                status=(
                    "warning"
                    if repos_requiring_attention
                    else "healthy"
                ),
            ),
        ]

    # =============================================================
    # Attention items
    # =============================================================

    async def _build_attention_items(
        self,
        organization_id: str,
        repos: list[dict],
        repo_names: dict[str, str],
        has_data: bool,
    ) -> list[AttentionItem]:

        items: list[AttentionItem] = []
        seen: set[str] = set()

        def add(item: AttentionItem) -> None:
            if item.id in seen:
                return

            seen.add(item.id)
            items.append(item)

        # Repository analysis problems
        for repo in repos:
            repo_id = str(repo["id"])

            name = repo_names.get(
                repo_id,
                repo.get("name", ""),
            )

            status = str(
                repo.get(
                    "analysis_status",
                    "not_started",
                )
            )

            if status == "failed":
                add(
                    AttentionItem(
                        id=f"repo-failed-{repo_id}",
                        title=f"Analysis failed for {name}",
                        description=(
                            "The latest repository analysis "
                            "did not complete successfully."
                        ),
                        severity="high",
                        href=f"/app/repositories/{repo_id}",
                        created_at=(
                            format_datetime(
                                repo.get("updated_at")
                            )
                            or ""
                        ),
                        entity_type="repository",
                        repository_id=repo_id,
                        repository_name=name,
                        action_label="View repository",
                    )
                )

            elif status == "not_started":
                add(
                    AttentionItem(
                        id=f"repo-not-started-{repo_id}",
                        title=f"{name} has not been analyzed",
                        description=(
                            "Run analysis to establish "
                            "security and quality baselines."
                        ),
                        severity="medium",
                        href=f"/app/repositories/{repo_id}",
                        created_at=(
                            format_datetime(
                                repo.get("created_at")
                            )
                            or ""
                        ),
                        entity_type="repository",
                        repository_id=repo_id,
                        repository_name=name,
                        action_label="Analyze repository",
                    )
                )

        if has_data:
            # Security findings
            critical_findings = (
                await self._findings.list_by_organization(
                    organization_id,
                    categories=[
                        "security",
                        "secret",
                        "dependency",
                    ],
                    limit=8,
                )
            )

            for finding in critical_findings:
                severity = finding.get("severity")

                if severity not in {"critical", "high"}:
                    continue

                repo_id = str(
                    finding.get("repository_id", "")
                )

                add(
                    AttentionItem(
                        id=f"finding-{finding['id']}",
                        title=finding.get(
                            "title",
                            "Security finding",
                        ),
                        description=(
                            finding.get("description")
                            or finding.get("file", "")
                        ),
                        severity=severity,
                        href="/app/security",
                        created_at=(
                            format_datetime(
                                finding.get("created_at")
                            )
                            or ""
                        ),
                        entity_type="finding",
                        repository_id=(
                            repo_id or None
                        ),
                        repository_name=(
                            repo_names.get(repo_id)
                        ),
                        action_label="View findings",
                    )
                )

            # High-risk PRs
            high_risk_prs = (
                await self._pull_requests.list_high_risk_by_organization(
                    organization_id,
                    limit=5,
                )
            )

            for pr in high_risk_prs:
                risk_score = pr.get("risk_score")

                if not isinstance(
                    risk_score,
                    (int, float),
                ):
                    continue

                pr_id = int(
                    pr.get(
                        "id",
                        pr.get("github_id", 0),
                    )
                )

                add(
                    AttentionItem(
                        id=f"pr-{pr_id}",
                        title=(
                            f"High-risk PR: "
                            f"{pr.get('title', '')}"
                        ),
                        description=(
                            f"Risk score {int(risk_score)} "
                            f"on "
                            f"{pr.get('repository_name', '')}"
                        ),
                        severity=(
                            "critical"
                            if risk_score >= 70
                            else "high"
                        ),
                        href=f"/app/pull-requests/{pr_id}",
                        created_at=(
                            format_datetime(
                                pr.get("updated_at")
                                or pr.get("created_at")
                            )
                            or ""
                        ),
                        entity_type="pull_request",
                        repository_name=pr.get(
                            "repository_name"
                        ),
                        action_label="Review pull request",
                    )
                )

            # Failed analysis runs
            failed_runs = (
                await self._analysis_runs.list_failed_recent(
                    organization_id,
                    limit=3,
                )
            )

            for run in failed_runs:
                repo_id = str(
                    run.get("repository_id", "")
                )

                add(
                    AttentionItem(
                        id=f"analysis-failed-{run['id']}",
                        title=(
                            "Analysis failed for "
                            f"{repo_names.get(repo_id, 'repository')}"
                        ),
                        description=(
                            run.get("error")
                            or "Analysis did not complete."
                        ),
                        severity="high",
                        href=f"/app/repositories/{repo_id}",
                        created_at=(
                            format_datetime(
                                run.get("completed_at")
                                or run.get("created_at")
                            )
                            or ""
                        ),
                        entity_type="analysis",
                        repository_id=repo_id,
                        repository_name=repo_names.get(
                            repo_id
                        ),
                        action_label="View repository",
                    )
                )

        return items[:12]

    # =============================================================
    # Repository items
    # =============================================================

    def _build_repository_items(
        self,
        repos: list[dict],
    ) -> list[RepositoryDashboardItem]:

        items: list[RepositoryDashboardItem] = []

        for repo in repos:
            items.append(
                RepositoryDashboardItem(
                    id=repo["id"],
                    name=(
                        repo.get("full_name")
                        or repo.get("name", "")
                    ),
                    health_score=repo.get(
                        "health_score"
                    ),
                    security_score=repo.get(
                        "security_score"
                    ),
                    code_quality_score=repo.get(
                        "code_quality_score"
                    ),
                    open_pull_requests=int(
                        repo.get(
                            "open_pull_requests",
                            0,
                        )
                    ),
                    analysis_status=str(
                        repo.get(
                            "analysis_status",
                            "not_started",
                        )
                    ),
                    last_analyzed_at=format_datetime(
                        repo.get("last_analyzed_at")
                    ),
                    risk_level=repo.get("risk_level"),
                )
            )

        # Highest health first.
        # Unanalyzed repositories go to the bottom.
        items.sort(
            key=lambda item: (
                item.health_score is None,
                -(item.health_score or 0),
            )
        )

        return items

    # =============================================================
    # Pull requests
    # =============================================================

    async def _build_pull_request_section(
        self,
        organization_id: str,
    ) -> PullRequestSection:

        high_risk_docs = (
            await self._pull_requests.list_high_risk_by_organization(
                organization_id,
                limit=8,
            )
        )

        awaiting_docs = (
            await self._pull_requests.list_awaiting_risk(
                organization_id,
                limit=5,
            )
        )

        recent_docs = (
            await self._pull_requests.list_recently_scored(
                organization_id,
                limit=5,
            )
        )

        return PullRequestSection(
            high_risk=[
                self._to_pr_item(doc)
                for doc in high_risk_docs
            ],
            awaiting_analysis=[
                self._to_pr_item(doc)
                for doc in awaiting_docs
            ],
            recently_analyzed=[
                self._to_pr_item(doc)
                for doc in recent_docs
            ],
        )

    def _to_pr_item(
        self,
        doc: dict,
    ) -> PullRequestDashboardItem:

        risk_score = doc.get("risk_score")

        score = (
            int(risk_score)
            if isinstance(
                risk_score,
                (int, float),
            )
            else None
        )

        verdict, label, reason = pr_verdict(score)

        return PullRequestDashboardItem(
            id=int(
                doc.get(
                    "id",
                    doc.get("github_id", 0),
                )
            ),
            repository_id=str(
                doc.get("repository_id", "")
            ),
            repository_name=str(
                doc.get("repository_name", "")
            ),
            title=str(
                doc.get("title", "")
            ),
            risk_score=score,
            risk_level=pr_risk_level(score),
            verdict=verdict,
            verdict_label=label,
            verdict_reason=reason,
            updated_at=format_datetime(
                doc.get("risk_scored_at")
                or doc.get("updated_at")
            ),
            status=str(
                doc.get(
                    "status",
                    "open",
                )
            ),
            issues_count=int(
                doc.get(
                    "issues_count",
                    0,
                )
            ),
        )

    # =============================================================
    # Analysis activity
    # =============================================================

    async def _build_analysis_activity(
        self,
        organization_id: str,
        repo_names: dict[str, str],
    ) -> list[AnalysisActivityItem]:

        runs = (
            await self._analysis_runs.list_recent_by_organization(
                organization_id,
                limit=8,
            )
        )

        items: list[AnalysisActivityItem] = []

        for run in runs:
            repo_id = str(
                run.get("repository_id", "")
            )

            health_snapshot = run.get(
                "health_snapshot"
            )

            health_score = None

            if (
                isinstance(
                    health_snapshot,
                    dict,
                )
                and health_snapshot.get(
                    "health_score"
                )
                is not None
            ):
                health_score = float(
                    health_snapshot["health_score"]
                )

            items.append(
                AnalysisActivityItem(
                    id=run["id"],
                    repository_id=repo_id,
                    repository_name=repo_names.get(
                        repo_id,
                        "Repository",
                    ),
                    commit_sha=run.get(
                        "commit_sha"
                    ),
                    trigger_source=str(
                        run.get(
                            "trigger_source"
                        )
                        or run.get(
                            "trigger",
                            "manual",
                        )
                    ),
                    started_at=format_datetime(
                        run.get("started_at")
                    ),
                    completed_at=format_datetime(
                        run.get("completed_at")
                    ),
                    duration_seconds=duration_seconds(
                        run.get("started_at"),
                        run.get("completed_at"),
                    ),
                    status=str(
                        run.get(
                            "status",
                            "queued",
                        )
                    ),
                    error=run.get("error"),
                    finding_count=int(
                        run.get(
                            "finding_count",
                            0,
                        )
                    ),
                    health_score=health_score,
                    href=(
                        f"/app/analysis-runs/"
                        f"{run['id']}"
                    ),
                )
            )

        return items

    # =============================================================
    # Risk distribution
    # =============================================================

    def _build_risk_distribution(
        self,
        severity_counts: SeverityCounts | None,
        has_data: bool,
    ) -> RiskDistribution:

        if (
            not has_data
            or severity_counts is None
        ):
            return RiskDistribution(
                buckets=[],
                total=0,
                has_data=False,
            )

        buckets = [
            RiskDistributionBucket(
                key="critical",
                label="Critical",
                count=severity_counts.critical,
            ),
            RiskDistributionBucket(
                key="high",
                label="High",
                count=severity_counts.high,
            ),
            RiskDistributionBucket(
                key="medium",
                label="Medium",
                count=severity_counts.medium,
            ),
            RiskDistributionBucket(
                key="low",
                label="Low",
                count=severity_counts.low,
            ),
        ]

        total = sum(
            bucket.count
            for bucket in buckets
        )

        return RiskDistribution(
            buckets=buckets,
            total=total,
            has_data=total > 0,
        )

    # =============================================================
    # Recommended actions
    # =============================================================

    def _build_recommended_actions(
        self,
        *,
        repo_count: int,
        has_data: bool,
        repos_requiring_attention: int,
        critical_count: int,
        has_active: bool,
    ) -> list[RecommendedAction]:

        actions: list[RecommendedAction] = []

        if repo_count == 0:
            actions.append(
                RecommendedAction(
                    id="connect-repo",
                    label="Connect a repository",
                    description=(
                        "Link a GitHub repository "
                        "to start engineering analysis."
                    ),
                    href="/app/repositories/connect",
                    priority="high",
                )
            )

        elif not has_data:
            actions.append(
                RecommendedAction(
                    id="run-analysis",
                    label="Run repository analysis",
                    description=(
                        "Complete your first analysis "
                        "to populate engineering health metrics."
                    ),
                    href="/app/repositories",
                    priority="high",
                )
            )

        if critical_count:
            actions.append(
                RecommendedAction(
                    id="review-critical",
                    label="Review critical findings",
                    description=(
                        f"{critical_count} critical finding(s) "
                        "require immediate attention."
                    ),
                    href="/app/security",
                    priority="high",
                )
            )

        if (
            repos_requiring_attention
            and has_data
        ):
            actions.append(
                RecommendedAction(
                    id="review-repos",
                    label=(
                        "Review repositories "
                        "requiring attention"
                    ),
                    description=(
                        "Repositories have failed analysis "
                        "or elevated risk signals."
                    ),
                    href="/app/repositories",
                    priority="medium",
                )
            )

        if has_active:
            actions.append(
                RecommendedAction(
                    id="monitor-analysis",
                    label="Monitor running analysis",
                    description=(
                        "Analysis is in progress. "
                        "Refresh to see updated status."
                    ),
                    href="/app/repositories",
                    priority="low",
                )
            )

        return actions