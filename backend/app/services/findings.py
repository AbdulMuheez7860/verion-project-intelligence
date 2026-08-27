from typing import Any

from app.schemas.ai import FindingAIExplanation

from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.repositories import RepositoryRepository

from app.schemas.findings import (
    DependencyResponse,
    DependencySummary,
    FindingDetailResponse,
    QualityFindingResponse,
    QualitySummary,
    SecurityFindingResponse,
    SecuritySummary,
    SeverityCounts,
)

from app.schemas.pagination import PaginatedResponse

from app.schemas.quality_intelligence import (
    QualityFreshness,
    QualityIntelligenceResponse,
    QualityPosture,
    QualityRecommendation,
    QualityRepositorySummary,
    QualityRuleSummary,
    QualityScannerCoverage,
    QualityTotals,
    UnavailableQualityMetric,
)

from app.schemas.security_intelligence import (
    ScannerCoverage,
    SecurityCategoryCounts,
    SecurityFreshness,
    SecurityIntelligenceResponse,
    SecurityPosture,
    SecurityRepositoryOption,
    SecurityTotals,
)

from app.schemas.dependency_intelligence import (
    DependencyFreshness,
    DependencyIntelligenceResponse,
    DependencyPackageSummary,
    DependencyPosture,
    DependencyRecommendation,
    DependencyRepositorySummary,
    DependencyScannerCoverage,
    DependencyTotals,
    EcosystemCoverage,
    UnavailableDependencyMetric,
)

from app.lib.secret_redaction import redact_sensitive_text

from app.lib.quality_helpers import (
    QUALITY_CATEGORIES,
    SUPPORTED_QUALITY_SCANNERS,
    UNAVAILABLE_QUALITY_METRICS,
    build_quality_freshness,
    build_quality_posture,
    build_quality_recommendations,
    filter_quality_scanners,
)

from app.lib.dependency_helpers import (
    ECOSYSTEM_COVERAGE,
    SUPPORTED_SCANNERS as DEPENDENCY_SUPPORTED_SCANNERS,
    UNAVAILABLE_DEPENDENCY_METRICS,
    build_dependency_freshness,
    build_dependency_posture,
    build_dependency_recommendations,
)

from app.lib.dashboard_helpers import format_datetime

from app.lib.security_helpers import (
    SECURITY_CATEGORIES,
    SUPPORTED_SCANNERS,
    build_security_freshness,
    build_security_posture,
    is_repository_analysis_stale,
    normalize_scanner_name,
)

from app.services.risk_engine import compute_risk_metrics

from app.services.pr_risk_engine import (
    PRRiskScore,
    PRRiskSignals,
    compute_pr_risk_score,
    filter_findings_for_changed_files,
)


class FindingsService:
    def __init__(
        self,
        findings: FindingRepository,
        dependencies: DependencyRepository,
        analysis_runs: AnalysisRunRepository,
        repositories: RepositoryRepository,
    ) -> None:
        self._findings = findings
        self._dependencies = dependencies
        self._analysis_runs = analysis_runs
        self._repositories = repositories

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _has_analysis_data(self, organization_id: str) -> bool:
        return await self._analysis_runs.has_completed_for_organization(
            organization_id
        )

    async def _repository_names(
        self,
        organization_id: str,
    ) -> dict[str, str]:
        repos = await self._repositories.list_by_organization(
            organization_id
        )

        return {
            repo["id"]: repo.get("full_name") or repo.get("name", "")
            for repo in repos
        }

    # ------------------------------------------------------------------
    # PR RISK ENGINE
    # ------------------------------------------------------------------

    def compute_pr_risk(
        self,
        *,
        security_findings: list[dict[str, Any]],
        files_changed: int,
        additions: int,
        deletions: int,
        changed_files: list[str],
        coverage_percent: float | None = None,
        dependency_vulnerabilities: int = 0,
        repository_risk_level: str | None = None,
        prior_pr_risk_average: float | None = None,
    ) -> PRRiskScore:
        """
        Compute risk for a single pull request.

        PR risk is intentionally different from repository-wide risk.

        Only security findings belonging to files changed by the PR
        are included in the security component of the score.
        """

        changed_findings = filter_findings_for_changed_files(
            security_findings,
            changed_files,
        )

        signals = PRRiskSignals(
            security_findings=changed_findings,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            changed_files=changed_files,
            coverage_percent=coverage_percent,
            dependency_vulnerabilities=dependency_vulnerabilities,
            repository_risk_level=repository_risk_level,
            prior_pr_risk_average=prior_pr_risk_average,
        )

        return compute_pr_risk_score(signals)

    async def compute_organization_pr_risk(
        self,
        organization_id: str,
        *,
        files_changed: int,
        additions: int,
        deletions: int,
        changed_files: list[str],
        coverage_percent: float | None = None,
        dependency_vulnerabilities: int = 0,
        repository_risk_level: str | None = None,
        prior_pr_risk_average: float | None = None,
    ) -> PRRiskScore:
        """
        Compute PR risk using security findings stored for the
        organization.

        The PR-specific changed-file filter is applied before scoring.
        """

        findings = await self._findings.list_by_organization(
            organization_id,
            categories=list(SECURITY_CATEGORIES),
        )

        return self.compute_pr_risk(
            security_findings=findings,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            changed_files=changed_files,
            coverage_percent=coverage_percent,
            dependency_vulnerabilities=dependency_vulnerabilities,
            repository_risk_level=repository_risk_level,
            prior_pr_risk_average=prior_pr_risk_average,
        )

    # ------------------------------------------------------------------
    # SECURITY
    # ------------------------------------------------------------------

    async def security_summary(
        self,
        organization_id: str,
    ) -> SecuritySummary:
        intelligence = await self.security_intelligence(
            organization_id
        )

        return SecuritySummary(
            score=intelligence.score,
            severity_counts=intelligence.severity_counts,
            has_analysis_data=intelligence.has_analysis_data,
        )

    async def security_intelligence(
        self,
        organization_id: str,
    ) -> SecurityIntelligenceResponse:
        has_data = await self._has_analysis_data(
            organization_id
        )

        analysis_running = (
            await self._analysis_runs.has_active_for_organization(
                organization_id
            )
        )

        repos = await self._repositories.list_by_organization(
            organization_id
        )

        repo_names = {
            repo["id"]: repo.get("full_name")
            or repo.get("name", "")
            for repo in repos
        }

        if not has_data:
            posture = SecurityPosture(
                **build_security_posture(
                    score=None,
                    severity_counts={},
                    has_analysis_data=False,
                )
            )

            freshness = SecurityFreshness(
                **build_security_freshness(
                    has_analysis_data=False,
                    analysis_running=analysis_running,
                    last_analyzed_at=None,
                    repositories_failed=0,
                    repositories_stale=0,
                )
            )

            return SecurityIntelligenceResponse(
                has_analysis_data=False,
                posture=posture,
                freshness=freshness,
                totals=SecurityTotals(
                    connected_repositories=len(repos)
                ),
                category_counts=SecurityCategoryCounts(),
                scanner_coverage=ScannerCoverage(
                    supported=list(SUPPORTED_SCANNERS),
                    note=(
                        "Scanner coverage appears after the first "
                        "completed repository analysis."
                    ),
                ),
                repositories=[
                    SecurityRepositoryOption(
                        id=repo["id"],
                        name=repo_names[repo["id"]],
                        finding_count=0,
                    )
                    for repo in repos
                ],
            )

        counts = await self._findings.count_by_severity(
            organization_id,
            list(SECURITY_CATEGORIES),
        )

        category_counts_raw = (
            await self._findings.count_by_category(
                organization_id
            )
        )

        findings = await self._findings.list_by_organization(
            organization_id,
            categories=list(SECURITY_CATEGORIES),
        )

        metrics = compute_risk_metrics(findings)

        open_count = await self._findings.count_open_security(
            organization_id
        )

        total_count = sum(counts.values())

        repositories_affected = (
            await self._findings.count_repositories_with_findings(
                organization_id
            )
        )

        findings_by_repo = (
            await self._findings.count_by_repository(
                organization_id
            )
        )

        repositories_failed = sum(
            1
            for repo in repos
            if str(repo.get("analysis_status", "")) == "failed"
        )

        repositories_stale = sum(
            1
            for repo in repos
            if repo.get("analysis_status") == "complete"
            and is_repository_analysis_stale(
                repo.get("last_analyzed_at")
            )
        )

        last_analyzed_at = (
            await self._analysis_runs.latest_completed_at_for_organization(
                organization_id
            )
        )

        executed_scanners: set[str] = set()

        summaries = (
            await self._analysis_runs.list_latest_completed_summaries(
                organization_id
            )
        )

        for summary in summaries:
            analyzer_summary = summary.get(
                "analyzer_summary"
            )

            if not isinstance(analyzer_summary, dict):
                continue

            executed = analyzer_summary.get("executed")

            if isinstance(executed, list):
                for name in executed:
                    if isinstance(name, str) and name.strip():
                        executed_scanners.add(
                            normalize_scanner_name(
                                name.strip()
                            )
                        )

        posture = SecurityPosture(
            **build_security_posture(
                score=metrics.security_score,
                severity_counts=counts,
                has_analysis_data=True,
            )
        )

        freshness = SecurityFreshness(
            **build_security_freshness(
                has_analysis_data=True,
                analysis_running=analysis_running,
                last_analyzed_at=last_analyzed_at,
                repositories_failed=repositories_failed,
                repositories_stale=repositories_stale,
            )
        )

        return SecurityIntelligenceResponse(
            score=metrics.security_score,
            severity_counts=SeverityCounts(
                **counts
            ),
            has_analysis_data=True,
            posture=posture,
            freshness=freshness,
            totals=SecurityTotals(
                open=open_count,
                total=total_count,
                repositories_affected=repositories_affected,
                connected_repositories=len(repos),
            ),
            category_counts=SecurityCategoryCounts(
                security=category_counts_raw.get(
                    "security",
                    0,
                ),
                secret=category_counts_raw.get(
                    "secret",
                    0,
                ),
                dependency=category_counts_raw.get(
                    "dependency",
                    0,
                ),
            ),
            scanner_coverage=ScannerCoverage(
                executed=sorted(executed_scanners),
                supported=list(SUPPORTED_SCANNERS),
                has_data=bool(executed_scanners),
                note=(
                    "Coverage reflects scanners executed in the "
                    "latest completed analysis per repository."
                    if executed_scanners
                    else "No scanner execution data recorded yet."
                ),
            ),
            repositories=[
                SecurityRepositoryOption(
                    id=repo["id"],
                    name=repo_names[repo["id"]],
                    finding_count=findings_by_repo.get(
                        repo["id"],
                        0,
                    ),
                )
                for repo in repos
            ],
        )

    async def security_findings(
        self,
        organization_id: str,
    ) -> list[SecurityFindingResponse]:
        page = await self.security_findings_paginated(
            organization_id,
            page=1,
            page_size=10_000,
        )

        return page.items

    async def security_findings_paginated(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        repository_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        category: str | None = None,
        sort: str = "severity",
        order: str = "desc",
    ) -> PaginatedResponse[SecurityFindingResponse]:

        if not await self._has_analysis_data(
            organization_id
        ):
            return PaginatedResponse.build(
                [],
                total=0,
                page=page,
                page_size=page_size,
            )

        categories = (
            [category]
            if category
            else list(SECURITY_CATEGORIES)
        )

        repo_names = await self._repository_names(
            organization_id
        )

        repository_ids_for_search: list[str] | None = None

        if q:
            query = q.lower()

            repository_ids_for_search = [
                repo_id
                for repo_id, name in repo_names.items()
                if query in name.lower()
            ]

        skip = (page - 1) * page_size

        docs, total = (
            await self._findings.list_security_paginated(
                organization_id,
                categories=categories,
                repository_id=repository_id,
                severity=severity,
                status=status,
                q=q,
                repository_ids_for_search=repository_ids_for_search,
                sort=sort,
                order=order,
                skip=skip,
                limit=page_size,
            )
        )

        items = [
            self._to_security_finding(
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

    # ------------------------------------------------------------------
    # QUALITY
    # ------------------------------------------------------------------

    async def quality_summary(
        self,
        organization_id: str,
    ) -> QualitySummary:
        intelligence = await self.quality_intelligence(
            organization_id
        )

        return QualitySummary(
            score=intelligence.score,
            maintainability_score=intelligence.score,
            has_analysis_data=intelligence.has_analysis_data,
        )

    async def quality_intelligence(
        self,
        organization_id: str,
    ) -> QualityIntelligenceResponse:
        has_data = await self._has_analysis_data(
            organization_id
        )

        analysis_running = (
            await self._analysis_runs.has_active_for_organization(
                organization_id
            )
        )

        repos = await self._repositories.list_by_organization(
            organization_id
        )

        repo_names = {
            repo["id"]: repo.get("full_name")
            or repo.get("name", "")
            for repo in repos
        }

        unavailable_metrics = [
            UnavailableQualityMetric(**metric)
            for metric in UNAVAILABLE_QUALITY_METRICS
        ]

        if not has_data:
            posture = QualityPosture(
                **build_quality_posture(
                    score=None,
                    severity_counts={},
                    has_analysis_data=False,
                )
            )

            freshness = QualityFreshness(
                **build_quality_freshness(
                    has_analysis_data=False,
                    analysis_running=analysis_running,
                    last_analyzed_at=None,
                    repositories_failed=0,
                    repositories_stale=0,
                )
            )

            return QualityIntelligenceResponse(
                has_analysis_data=False,
                posture=posture,
                freshness=freshness,
                totals=QualityTotals(
                    connected_repositories=len(repos)
                ),
                scanner_coverage=QualityScannerCoverage(
                    supported=list(
                        SUPPORTED_QUALITY_SCANNERS
                    ),
                    note=(
                        "Scanner coverage appears after the first "
                        "completed repository analysis."
                    ),
                ),
                repositories=[
                    QualityRepositorySummary(
                        id=repo["id"],
                        name=repo_names[repo["id"]],
                        analysis_status=repo.get(
                            "analysis_status"
                        ),
                    )
                    for repo in repos
                ],
                unavailable_metrics=unavailable_metrics,
            )

        categories = list(QUALITY_CATEGORIES)

        counts = await self._findings.count_by_severity(
            organization_id,
            categories,
        )

        open_count = (
            await self._findings.count_open_for_categories(
                organization_id,
                categories=categories,
            )
        )

        total_count = sum(counts.values())

        repositories_affected = (
            await self._findings.count_repositories_with_findings(
                organization_id,
                categories=categories,
            )
        )

        repo_stats = await self._findings.repository_stats(
            organization_id,
            categories=categories,
        )

        repo_stats_by_id = {
            row["repository_id"]: row
            for row in repo_stats
        }

        top_rules_raw = await self._findings.top_rules(
            organization_id,
            categories=categories,
            limit=8,
        )

        findings = await self._findings.list_by_organization(
            organization_id,
            categories=categories,
        )

        metrics = compute_risk_metrics(findings)

        repositories_failed = sum(
            1
            for repo in repos
            if str(repo.get("analysis_status", "")) == "failed"
        )

        repositories_stale = sum(
            1
            for repo in repos
            if repo.get("analysis_status") == "complete"
            and is_repository_analysis_stale(
                repo.get("last_analyzed_at")
            )
        )

        last_analyzed_at = (
            await self._analysis_runs.latest_completed_at_for_organization(
                organization_id
            )
        )

        executed_scanners: set[str] = set()

        summaries = (
            await self._analysis_runs.list_latest_completed_summaries(
                organization_id
            )
        )

        for summary in summaries:
            analyzer_summary = summary.get(
                "analyzer_summary"
            )

            if not isinstance(analyzer_summary, dict):
                continue

            executed = analyzer_summary.get("executed")

            if isinstance(executed, list):
                for name in executed:
                    if isinstance(name, str) and name.strip():
                        executed_scanners.add(
                            normalize_scanner_name(
                                name.strip()
                            )
                        )

        quality_scanners = filter_quality_scanners(
            executed_scanners
        )

        repository_summaries: list[
            QualityRepositorySummary
        ] = []

        for repo in repos:
            stats = repo_stats_by_id.get(
                repo["id"],
                {},
            )

            repository_summaries.append(
                QualityRepositorySummary(
                    id=repo["id"],
                    name=repo_names[repo["id"]],
                    finding_count=int(
                        stats.get(
                            "finding_count",
                            0,
                        )
                    ),
                    open_count=int(
                        stats.get(
                            "open_count",
                            0,
                        )
                    ),
                    highest_severity=stats.get(
                        "highest_severity"
                    ),
                    quality_score=repo.get(
                        "code_quality_score"
                    ),
                    analysis_status=repo.get(
                        "analysis_status"
                    ),
                    last_analyzed_at=format_datetime(
                        repo.get(
                            "last_analyzed_at"
                        )
                    ),
                )
            )

        repository_summaries.sort(
            key=lambda item: item.finding_count,
            reverse=True,
        )

        recommendations_raw = (
            build_quality_recommendations(
                severity_counts=counts,
                top_rules=top_rules_raw,
                repositories=[
                    summary.model_dump()
                    for summary in repository_summaries
                ],
                repositories_stale=repositories_stale,
                analysis_running=analysis_running,
            )
        )

        posture = QualityPosture(
            **build_quality_posture(
                score=metrics.code_quality_score,
                severity_counts=counts,
                has_analysis_data=True,
            )
        )

        freshness = QualityFreshness(
            **build_quality_freshness(
                has_analysis_data=True,
                analysis_running=analysis_running,
                last_analyzed_at=last_analyzed_at,
                repositories_failed=repositories_failed,
                repositories_stale=repositories_stale,
            )
        )

        return QualityIntelligenceResponse(
            score=metrics.code_quality_score,
            severity_counts=SeverityCounts(
                **counts
            ),
            has_analysis_data=True,
            posture=posture,
            freshness=freshness,
            totals=QualityTotals(
                open=open_count,
                total=total_count,
                repositories_affected=repositories_affected,
                connected_repositories=len(repos),
                critical=int(
                    counts.get("critical", 0)
                ),
                high=int(
                    counts.get("high", 0)
                ),
            ),
            scanner_coverage=QualityScannerCoverage(
                executed=sorted(
                    quality_scanners
                ),
                supported=list(
                    SUPPORTED_QUALITY_SCANNERS
                ),
                has_data=bool(
                    quality_scanners
                ),
                note=(
                    "Coverage reflects Ruff and ESLint "
                    "execution in the latest completed "
                    "analysis per repository."
                    if quality_scanners
                    else "No quality scanner execution "
                    "data recorded yet."
                ),
            ),
            repositories=repository_summaries,
            top_rules=[
                QualityRuleSummary(
                    rule_id=str(
                        rule.get(
                            "rule_id",
                            "unknown",
                        )
                    ),
                    analyzer=rule.get(
                        "analyzer"
                    ),
                    count=int(
                        rule.get(
                            "count",
                            0,
                        )
                    ),
                    highest_severity=str(
                        rule.get(
                            "highest_severity",
                            "low",
                        )
                    ),
                    repository_count=int(
                        rule.get(
                            "repository_count",
                            0,
                        )
                    ),
                )
                for rule in top_rules_raw
            ],
            unavailable_metrics=unavailable_metrics,
            recommendations=[
                QualityRecommendation(
                    **rec
                )
                for rec in recommendations_raw
            ],
        )

    async def quality_findings(
        self,
        organization_id: str,
    ) -> list[QualityFindingResponse]:
        page = await self.quality_findings_paginated(
            organization_id,
            page=1,
            page_size=10_000,
        )

        return page.items

    async def quality_findings_paginated(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        repository_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        rule_id: str | None = None,
        sort: str = "severity",
        order: str = "desc",
    ) -> PaginatedResponse[QualityFindingResponse]:

        if not await self._has_analysis_data(
            organization_id
        ):
            return PaginatedResponse.build(
                [],
                total=0,
                page=page,
                page_size=page_size,
            )

        repo_names = await self._repository_names(
            organization_id
        )

        repository_ids_for_search: list[str] | None = None

        if q:
            query = q.lower()

            repository_ids_for_search = [
                rid
                for rid, name in repo_names.items()
                if query in name.lower()
            ]

        skip = (page - 1) * page_size

        docs, total = (
            await self._findings.list_quality_paginated(
                organization_id,
                repository_id=repository_id,
                severity=severity,
                status=status,
                rule_id=rule_id,
                q=q,
                repository_ids_for_search=repository_ids_for_search,
                sort=sort,
                order=order,
                skip=skip,
                limit=page_size,
            )
        )

        items = [
            self._to_quality_finding(
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

    # ------------------------------------------------------------------
    # DEPENDENCIES
    # ------------------------------------------------------------------

    async def dependency_summary(
        self,
        organization_id: str,
    ) -> DependencySummary:
        intelligence = await self.dependency_intelligence(
            organization_id
        )

        vulnerable = intelligence.totals.vulnerable

        return DependencySummary(
            health_score=intelligence.health_score,
            total_packages=intelligence.totals.total,
            outdated_count=intelligence.totals.outdated,
            vulnerable_count=vulnerable,
            abandoned_count=0,
            has_analysis_data=intelligence.has_analysis_data,
        )

    async def dependency_intelligence(
        self,
        organization_id: str,
    ) -> DependencyIntelligenceResponse:
        has_data = await self._has_analysis_data(
            organization_id
        )

        analysis_running = (
            await self._analysis_runs.has_active_for_organization(
                organization_id
            )
        )

        repos = await self._repositories.list_by_organization(
            organization_id
        )

        repo_names = {
            repo["id"]: repo.get("full_name")
            or repo.get("name", "")
            for repo in repos
        }

        unavailable_metrics = [
            UnavailableDependencyMetric(**metric)
            for metric in UNAVAILABLE_DEPENDENCY_METRICS
        ]

        ecosystems = [
            EcosystemCoverage(**eco)
            for eco in ECOSYSTEM_COVERAGE
        ]

        if not has_data:
            posture = DependencyPosture(
                **build_dependency_posture(
                    health_score=None,
                    severity_counts={},
                    vulnerable_count=0,
                    has_analysis_data=False,
                )
            )

            freshness = DependencyFreshness(
                **build_dependency_freshness(
                    has_analysis_data=False,
                    analysis_running=analysis_running,
                    last_analyzed_at=None,
                    repositories_failed=0,
                    repositories_stale=0,
                )
            )

            return DependencyIntelligenceResponse(
                has_analysis_data=False,
                posture=posture,
                freshness=freshness,
                totals=DependencyTotals(
                    connected_repositories=len(repos)
                ),
                scanner_coverage=DependencyScannerCoverage(
                    supported=list(
                        DEPENDENCY_SUPPORTED_SCANNERS
                    ),
                    ecosystems=ecosystems,
                    note=(
                        "Scanner coverage appears after the first "
                        "completed repository analysis."
                    ),
                ),
                repositories=[
                    DependencyRepositorySummary(
                        id=repo["id"],
                        name=repo_names[repo["id"]],
                        analysis_status=repo.get(
                            "analysis_status"
                        ),
                    )
                    for repo in repos
                ],
                unavailable_metrics=unavailable_metrics,
            )

        dep_counts = await self._dependencies.summary_counts(
            organization_id
        )

        severity_counts = await self._findings.count_by_severity(
            organization_id,
            ["dependency"],
        )

        vulnerable_count = (
            dep_counts.get("vulnerable", 0)
            + dep_counts.get("critical", 0)
        )

        health_score = max(
            0.0,
            100.0 - (
                vulnerable_count * 10
            ),
        )

        repositories_affected = (
            await self._dependencies.count_repositories_with_vulnerabilities(
                organization_id
            )
        )

        repo_stats = (
            await self._dependencies.repository_stats(
                organization_id
            )
        )

        repo_stats_by_id = {
            row["repository_id"]: row
            for row in repo_stats
        }

        repo_severities = (
            await self._findings.dependency_highest_severity_by_repository(
                organization_id
            )
        )

        top_packages_raw = (
            await self._findings.dependency_top_packages(
                organization_id,
                limit=8,
            )
        )

        repositories_failed = sum(
            1
            for repo in repos
            if str(repo.get("analysis_status", "")) == "failed"
        )

        repositories_stale = sum(
            1
            for repo in repos
            if repo.get("analysis_status") == "complete"
            and is_repository_analysis_stale(
                repo.get("last_analyzed_at")
            )
        )

        last_analyzed_at = (
            await self._analysis_runs.latest_completed_at_for_organization(
                organization_id
            )
        )

        executed_scanners: set[str] = set()

        summaries = (
            await self._analysis_runs.list_latest_completed_summaries(
                organization_id
            )
        )

        for summary in summaries:
            analyzer_summary = summary.get(
                "analyzer_summary"
            )

            if not isinstance(analyzer_summary, dict):
                continue

            executed = analyzer_summary.get(
                "executed"
            )

            if isinstance(executed, list):
                for name in executed:
                    if isinstance(name, str) and name.strip():
                        executed_scanners.add(
                            normalize_scanner_name(
                                name.strip()
                            )
                        )

        dependency_scanners = sorted(
            name
            for name in executed_scanners
            if name == "pip-audit"
        )

        repository_summaries: list[
            DependencyRepositorySummary
        ] = []

        for repo in repos:
            stats = repo_stats_by_id.get(
                repo["id"],
                {},
            )

            repository_summaries.append(
                DependencyRepositorySummary(
                    id=repo["id"],
                    name=repo_names[repo["id"]],
                    dependency_count=int(
                        stats.get(
                            "dependency_count",
                            0,
                        )
                    ),
                    vulnerable_count=int(
                        stats.get(
                            "vulnerable_count",
                            0,
                        )
                    ),
                    highest_severity=repo_severities.get(
                        repo["id"]
                    ),
                    last_analyzed_at=format_datetime(
                        repo.get(
                            "last_analyzed_at"
                        )
                    ),
                    analysis_status=repo.get(
                        "analysis_status"
                    ),
                )
            )

        repository_summaries.sort(
            key=lambda item: item.vulnerable_count,
            reverse=True,
        )

        recommendations_raw = (
            build_dependency_recommendations(
                severity_counts=severity_counts,
                top_packages=top_packages_raw,
                repositories=[
                    summary.model_dump()
                    for summary in repository_summaries
                ],
                repositories_stale=repositories_stale,
                analysis_running=analysis_running,
                vulnerable_count=vulnerable_count,
            )
        )

        posture = DependencyPosture(
            **build_dependency_posture(
                health_score=health_score,
                severity_counts=severity_counts,
                vulnerable_count=vulnerable_count,
                has_analysis_data=True,
            )
        )

        freshness = DependencyFreshness(
            **build_dependency_freshness(
                has_analysis_data=True,
                analysis_running=analysis_running,
                last_analyzed_at=last_analyzed_at,
                repositories_failed=repositories_failed,
                repositories_stale=repositories_stale,
            )
        )

        return DependencyIntelligenceResponse(
            health_score=health_score,
            severity_counts=SeverityCounts(
                **severity_counts
            ),
            has_analysis_data=True,
            posture=posture,
            freshness=freshness,
            totals=DependencyTotals(
                total=dep_counts.get(
                    "total",
                    0,
                ),
                vulnerable=vulnerable_count,
                critical=dep_counts.get(
                    "critical",
                    0,
                ),
                healthy=dep_counts.get(
                    "healthy",
                    0,
                ),
                outdated=dep_counts.get(
                    "outdated",
                    0,
                ),
                repositories_affected=repositories_affected,
                connected_repositories=len(repos),
            ),
            scanner_coverage=DependencyScannerCoverage(
                executed=dependency_scanners,
                supported=list(
                    DEPENDENCY_SUPPORTED_SCANNERS
                ),
                has_data=bool(
                    dependency_scanners
                ),
                ecosystems=ecosystems,
                note=(
                    "Coverage reflects pip-audit execution "
                    "against dependency manifests in the latest "
                    "completed analysis per repository."
                    if dependency_scanners
                    else "No dependency scanner execution "
                    "data recorded yet."
                ),
            ),
            repositories=repository_summaries,
            top_packages=[
                DependencyPackageSummary(
                    package_name=str(
                        pkg.get(
                            "package_name",
                            "",
                        )
                    ),
                    count=int(
                        pkg.get(
                            "count",
                            0,
                        )
                    ),
                    vulnerable_count=int(
                        pkg.get(
                            "vulnerable_count",
                            0,
                        )
                    ),
                    highest_severity=str(
                        pkg.get(
                            "highest_severity",
                            "low",
                        )
                    ),
                    repository_count=int(
                        pkg.get(
                            "repository_count",
                            0,
                        )
                    ),
                    vulnerability=pkg.get(
                        "vulnerability"
                    ),
                )
                for pkg in top_packages_raw
            ],
            unavailable_metrics=unavailable_metrics,
            recommendations=[
                DependencyRecommendation(**rec)
                for rec in recommendations_raw
            ],
        )

    async def dependencies(
        self,
        organization_id: str,
    ) -> list[DependencyResponse]:
        page = await self.dependencies_paginated(
            organization_id,
            page=1,
            page_size=100,
        )

        return page.items

    async def dependencies_paginated(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        repository_id: str | None = None,
        status: str | None = None,
        ecosystem: str | None = None,
        severity: str | None = None,
        sort: str = "status",
        order: str = "desc",
    ) -> PaginatedResponse[DependencyResponse]:

        if ecosystem and ecosystem != "python":
            return PaginatedResponse.build(
                [],
                total=0,
                page=page,
                page_size=page_size,
            )

        if not await self._has_analysis_data(
            organization_id
        ):
            return PaginatedResponse.build(
                [],
                total=0,
                page=page,
                page_size=page_size,
            )

        repo_names = await self._repository_names(
            organization_id
        )

        repository_ids_for_search: list[str] | None = None

        if q:
            query = q.lower()

            repository_ids_for_search = [
                rid
                for rid, name in repo_names.items()
                if query in name.lower()
            ]

        package_keys_for_severity: (
            list[dict[str, str]] | None
        ) = None

        if severity:
            package_keys_for_severity = (
                await self._findings.dependency_package_keys_for_severity(
                    organization_id,
                    severity,
                )
            )

            if not package_keys_for_severity:
                return PaginatedResponse.build(
                    [],
                    total=0,
                    page=page,
                    page_size=page_size,
                )

        skip = (page - 1) * page_size

        docs, total = (
            await self._dependencies.list_paginated(
                organization_id,
                repository_id=repository_id,
                status=status,
                q=q,
                repository_ids_for_search=repository_ids_for_search,
                package_keys_for_severity=package_keys_for_severity,
                sort=sort,
                order=order,
                skip=skip,
                limit=page_size,
            )
        )

        severity_map = (
            await self._findings.dependency_package_severity_map(
                organization_id
            )
        )

        items = [
            self._to_dependency(
                doc,
                repo_names,
                severity_map=severity_map,
            )
            for doc in docs
        ]

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_dependency(
        self,
        dependency_id: str,
        organization_id: str,
    ) -> DependencyResponse | None:

        doc = await self._dependencies.get_by_id(
            dependency_id,
            organization_id,
        )

        if not doc:
            return None

        repo_names = await self._repository_names(
            organization_id
        )

        severity_map = (
            await self._findings.dependency_package_severity_map(
                organization_id
            )
        )

        return self._to_dependency(
            doc,
            repo_names,
            severity_map=severity_map,
        )

    # ------------------------------------------------------------------
    # FINDING DETAIL
    # ------------------------------------------------------------------

    async def get_finding(
        self,
        finding_id: str,
        organization_id: str,
    ) -> FindingDetailResponse | None:

        doc = await self._findings.get_by_id(
            finding_id,
            organization_id,
        )

        if not doc:
            return None

        repo_names = await self._repository_names(
            organization_id
        )

        return self._to_finding_detail(
            doc,
            repo_names,
        )

    # ------------------------------------------------------------------
    # FINDING CONVERSION
    # ------------------------------------------------------------------

    def _to_ai_explanation(
        self,
        payload: Any,
    ) -> FindingAIExplanation | None:

        if not isinstance(payload, dict):
            return None

        if not payload.get("explanation"):
            return None

        return FindingAIExplanation(
            explanation=str(
                payload.get(
                    "explanation",
                    "",
                )
            ),
            remediation_suggestion=str(
                payload.get(
                    "remediation_suggestion",
                    "",
                )
            ),
            generated_at=str(
                payload.get(
                    "generated_at",
                    "",
                )
            ),
            model=str(
                payload.get(
                    "model",
                    "unknown",
                )
            ),
            source=str(
                payload.get(
                    "source",
                    "ai",
                )
            ),
            disclaimer=str(
                payload.get(
                    "disclaimer",
                    (
                        "AI-generated explanation based on scanner "
                        "output. Does not replace static analysis "
                        "or change finding severity."
                    ),
                )
            ),
        )

    def _base_finding_fields(
        self,
        doc: dict[str, Any],
        repo_names: dict[str, str],
    ) -> dict[str, Any]:

        metadata = doc.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            metadata = {}

        description = doc.get(
            "description"
        )

        if doc.get("category") == "secret":
            description = redact_sensitive_text(
                description
            )

        created_at = doc.get(
            "created_at"
        )

        updated_at = doc.get(
            "updated_at"
        )

        return {
            "id": doc["id"],
            "title": doc.get(
                "title",
                "",
            ),
            "file": doc.get(
                "file",
                "",
            ),
            "line": int(
                doc.get(
                    "line",
                    1,
                )
            ),
            "severity": doc.get(
                "severity",
                "low",
            ),
            "status": doc.get(
                "status",
                "open",
            ),
            "category": doc.get(
                "category",
                "security",
            ),
            "description": description,
            "remediation": doc.get(
                "remediation"
            ),
            "repository_id": doc.get(
                "repository_id"
            ),
            "repository_name": repo_names.get(
                doc.get(
                    "repository_id",
                    "",
                ),
                "",
            ),
            "rule_id": doc.get(
                "rule_id"
            ),
            "scanner_engine": metadata.get(
                "engine"
            ),
            "ai_explanation": self._to_ai_explanation(
                doc.get(
                    "ai_explanation"
                )
            ),
            "created_at": (
                created_at.isoformat()
                if hasattr(
                    created_at,
                    "isoformat",
                )
                else created_at
            ),
            "updated_at": (
                updated_at.isoformat()
                if hasattr(
                    updated_at,
                    "isoformat",
                )
                else updated_at
            ),
        }

    def _to_finding_detail(
        self,
        doc: dict[str, Any],
        repo_names: dict[str, str],
    ) -> FindingDetailResponse:

        return FindingDetailResponse(
            **self._base_finding_fields(
                doc,
                repo_names,
            ),
            analysis_id=doc.get(
                "analysis_id"
            ),
        )

    def _to_security_finding(
        self,
        doc: dict[str, Any],
        repo_names: dict[str, str],
    ) -> SecurityFindingResponse:

        metadata = doc.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            metadata = {}

        return SecurityFindingResponse(
            **self._base_finding_fields(
                doc,
                repo_names,
            ),
            cwe=metadata.get(
                "cwe"
            )
            or None,
            cve=metadata.get(
                "cve"
            )
            or None,
        )

    def _to_quality_finding(
        self,
        doc: dict[str, Any],
        repo_names: dict[str, str],
    ) -> QualityFindingResponse:

        return QualityFindingResponse(
            **self._base_finding_fields(
                doc,
                repo_names,
            ),
            rule=doc.get(
                "rule_id",
                "",
            ),
        )

    def _to_dependency(
        self,
        doc: dict[str, Any],
        repo_names: dict[str, str],
        *,
        severity_map: dict[
            tuple[str, str],
            str
        ]
        | None = None,
    ) -> DependencyResponse:

        repository_id = doc.get(
            "repository_id",
            "",
        )

        package_name = doc.get(
            "package_name",
            "",
        )

        severity = None

        if (
            severity_map is not None
            and repository_id
            and package_name
        ):
            severity = severity_map.get(
                (
                    str(repository_id),
                    str(package_name),
                )
            )

        created_at = doc.get(
            "created_at"
        )

        analyzed_at = (
            created_at.isoformat()
            if hasattr(
                created_at,
                "isoformat",
            )
            else str(created_at)
            if created_at
            else None
        )

        dependency_source = str(
            doc.get(
                "source"
            )
            or doc.get(
                "manifest"
            )
            or "requirements.txt"
        )

        return DependencyResponse(
            id=doc["id"],
            package_name=package_name,
            current_version=doc.get(
                "current_version",
                "",
            ),
            latest_version=doc.get(
                "latest_version",
                "",
            ),
            status=doc.get(
                "status",
                "healthy",
            ),
            vulnerability=doc.get(
                "vulnerability"
            ),
            license=doc.get(
                "license",
                "unknown",
            ),
            repository_id=repository_id
            or None,
            repository_name=repo_names.get(
                repository_id,
                "",
            ),
            ecosystem=doc.get(
                "ecosystem",
                "python",
            ),
            source=dependency_source,
            severity=severity,
            scanner_engine=doc.get(
                "scanner_engine",
                "pip-audit",
            ),
            analyzed_at=analyzed_at,
        )