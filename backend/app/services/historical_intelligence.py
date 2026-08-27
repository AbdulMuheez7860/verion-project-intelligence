from datetime import UTC, datetime, timedelta
from typing import Any

from app.lib.dashboard_helpers import format_datetime
from app.lib.historical_helpers import (
    compare_metric,
    is_material_improvement,
    is_material_regression,
    overall_trend_direction,
    snapshot_trend_label,
)
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.analytics_overview import (
    AnalyticsBaseline,
    AnalyticsOverviewResponse,
    AnalyticsRepositoryComparison,
    AnalyticsRepositoryOption,
    AnalyticsTrendPoint,
    HistoricalChange,
    HistoricalFreshness,
)


DEFAULT_RANGE_DAYS = 90
MAX_RANGE_DAYS = 365
MAX_TREND_POINTS = 200


class HistoricalIntelligenceService:
    def __init__(
        self,
        snapshots: AnalysisSnapshotRepository,
        repositories: RepositoryRepository,
        analysis_runs: AnalysisRunRepository,
        pull_requests: PullRequestRepository,
    ) -> None:
        self._snapshots = snapshots
        self._repositories = repositories
        self._analysis_runs = analysis_runs
        self._pull_requests = pull_requests

    def _parse_date_range(
        self,
        *,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[datetime, datetime]:
        end = to_date or datetime.now(UTC)

        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        start = from_date or (
            end - timedelta(days=DEFAULT_RANGE_DAYS)
        )

        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)

        if (end - start).days > MAX_RANGE_DAYS:
            start = end - timedelta(days=MAX_RANGE_DAYS)

        return start, end

    async def get_overview(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> AnalyticsOverviewResponse:
        start, end = self._parse_date_range(
            from_date=from_date,
            to_date=to_date,
        )

        repos = await self._repositories.list_by_organization(
            organization_id
        )

        repo_names = {
            repo["id"]: repo.get("full_name") or repo.get("name", "")
            for repo in repos
        }

        baseline_stats = await self._snapshots.baseline_stats(
            organization_id
        )

        snapshot_count = int(
            baseline_stats.get("count", 0)
        )

        baseline_label = snapshot_trend_label(
            snapshot_count
        )

        baseline = AnalyticsBaseline(
            available=snapshot_count > 0,
            snapshot_count=snapshot_count,
            status=baseline_label,
            first_captured_at=format_datetime(
                baseline_stats.get("first_captured_at")
            ),
            last_captured_at=format_datetime(
                baseline_stats.get("last_captured_at")
            ),
            message=self._baseline_message(
                baseline_label
            ),
        )

        snapshots, _total = (
            await self._snapshots.list_for_organization(
                organization_id,
                repository_id=repository_id,
                from_date=start,
                to_date=end,
                limit=MAX_TREND_POINTS,
            )
        )

        freshness = await self._build_freshness(
            organization_id,
            repos,
            baseline_stats,
        )

        trend_points = [
            self._to_trend_point(doc, repo_names)
            for doc in snapshots
        ]

        repository_comparisons = (
            await self._build_repository_comparisons(
                organization_id,
                repos,
                repo_names,
            )
        )

        regressions, improvements = self._detect_changes(
            repository_comparisons
        )

        repository_options = []

        for repo in repos:
            repository_options.append(
                AnalyticsRepositoryOption(
                    id=repo["id"],
                    name=repo_names[repo["id"]],
                    snapshot_count=(
                        await self._snapshots.count_for_repository(
                            organization_id,
                            repo["id"],
                        )
                    ),
                )
            )

        return AnalyticsOverviewResponse(
            baseline=baseline,
            freshness=freshness,
            health_trend=self._score_trend(
                trend_points,
                "health_score",
            ),
            security_trend=self._score_trend(
                trend_points,
                "security_score",
            ),
            quality_trend=self._score_trend(
                trend_points,
                "quality_score",
            ),
            dependency_trend=self._score_trend(
                trend_points,
                "dependency_score",
            ),
            risk_trend=self._score_trend(
                trend_points,
                "pr_risk_score",
            ),
            finding_trend=self._finding_trend(
                trend_points
            ),
            repository_comparisons=repository_comparisons,
            regressions=regressions,
            improvements=improvements,
            repository_options=repository_options,
            range_days=min(
                (end - start).days or DEFAULT_RANGE_DAYS,
                MAX_RANGE_DAYS,
            ),
        )

    async def get_summary_trend_direction(
        self,
        organization_id: str,
    ) -> tuple[str, int, str | None]:
        repos = await self._repositories.list_by_organization(
            organization_id
        )

        repo_names = {
            repo["id"]: repo.get("full_name") or repo.get("name", "")
            for repo in repos
        }

        comparisons = await self._build_repository_comparisons(
            organization_id,
            repos,
            repo_names,
        )

        metric_comparisons: list[dict[str, Any]] = []

        for row in comparisons:
            if row.health_comparison:
                metric_comparisons.append(
                    row.health_comparison.model_dump()
                )

        direction = overall_trend_direction(
            metric_comparisons
        )

        snapshot_count = (
            await self._snapshots.count_for_organization(
                organization_id
            )
        )

        message = None

        if snapshot_count < 2:
            message = (
                "Run another analysis to start measuring change over time."
                if snapshot_count == 1
                else (
                    "Analytics will appear after Verion completes "
                    "its first repository analysis."
                )
            )

        return direction, snapshot_count, message

    def _baseline_message(
        self,
        status: str,
    ) -> str:
        if status == "building":
            return (
                "Analytics will appear after Verion completes "
                "its first repository analysis."
            )

        if status == "established":
            return (
                "Baseline established. Run another analysis "
                "to start measuring change over time."
            )

        return (
            "Historical trends are computed from completed "
            "analysis snapshots."
        )

    async def _build_freshness(
        self,
        organization_id: str,
        repos: list[dict[str, Any]],
        baseline_stats: dict[str, Any],
    ) -> HistoricalFreshness:
        last_snapshot = format_datetime(
            baseline_stats.get("last_captured_at")
        )

        last_analysis = (
            await self._analysis_runs.latest_completed_at_for_organization(
                organization_id
            )
        )

        never_analyzed = [
            repo.get("full_name") or repo.get("name", "")
            for repo in repos
            if repo.get("analysis_status")
            in {None, "not_started", "failed"}
        ]

        stale = [
            repo.get("full_name") or repo.get("name", "")
            for repo in repos
            if (
                repo.get("analysis_status") == "complete"
                and not repo.get("last_analyzed_at")
            )
        ]

        return HistoricalFreshness(
            last_snapshot_at=last_snapshot,
            last_analysis_at=format_datetime(
                last_analysis
            ),
            stale_repositories=stale[:10],
            never_analyzed_repositories=never_analyzed[:10],
        )

    def _to_trend_point(
        self,
        doc: dict[str, Any],
        repo_names: dict[str, str],
    ) -> AnalyticsTrendPoint:
        finding_counts = doc.get("finding_counts") or {}

        repository_id = str(
            doc.get("repository_id", "")
        )

        return AnalyticsTrendPoint(
            captured_at=format_datetime(
                doc.get("captured_at")
            ) or "",
            repository_id=repository_id,
            repository_name=repo_names.get(
                repository_id,
                "",
            ),
            health_score=doc.get("health_score"),
            security_score=doc.get("security_score"),
            quality_score=doc.get("quality_score"),
            dependency_score=doc.get("dependency_score"),
            pr_risk_score=doc.get("pr_risk_score"),
            finding_total=(
                int(finding_counts.get("total", 0))
                if finding_counts
                else None
            ),
            finding_critical=(
                int(finding_counts.get("critical", 0))
                if finding_counts
                else None
            ),
            finding_high=(
                int(finding_counts.get("high", 0))
                if finding_counts
                else None
            ),
            finding_medium=(
                int(finding_counts.get("medium", 0))
                if finding_counts
                else None
            ),
            finding_low=(
                int(finding_counts.get("low", 0))
                if finding_counts
                else None
            ),
        )

    def _score_trend(
        self,
        points: list[AnalyticsTrendPoint],
        field: str,
    ) -> list[dict[str, Any]]:
        return [
            {
                "capturedAt": point.captured_at,
                "repositoryId": point.repository_id,
                "repositoryName": point.repository_name,
                "value": getattr(point, field),
            }
            for point in points
            if getattr(point, field) is not None
        ]

    def _finding_trend(
        self,
        points: list[AnalyticsTrendPoint],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for point in points:
            if point.finding_total is None:
                continue

            results.append(
                {
                    "capturedAt": point.captured_at,
                    "repositoryId": point.repository_id,
                    "repositoryName": point.repository_name,
                    "total": point.finding_total,
                    "critical": point.finding_critical,
                    "high": point.finding_high,
                    "medium": point.finding_medium,
                    "low": point.finding_low,
                }
            )

        return results

    async def _build_repository_comparisons(
        self,
        organization_id: str,
        repos: list[dict[str, Any]],
        repo_names: dict[str, str],
    ) -> list[AnalyticsRepositoryComparison]:
        comparisons: list[AnalyticsRepositoryComparison] = []

        for repo in repos:
            latest, previous = (
                await self._snapshots.get_snapshot_comparison(
                    organization_id,
                    repo["id"],
                )
            )

            health_cmp = compare_metric(
                metric="health_score",
                current=(
                    latest.get("health_score")
                    if latest
                    else None
                ),
                previous=(
                    previous.get("health_score")
                    if previous
                    else None
                ),
                label="Health score",
            )

            security_cmp = compare_metric(
                metric="security_score",
                current=(
                    latest.get("security_score")
                    if latest
                    else None
                ),
                previous=(
                    previous.get("security_score")
                    if previous
                    else None
                ),
                label="Security score",
            )

            quality_cmp = compare_metric(
                metric="quality_score",
                current=(
                    latest.get("quality_score")
                    if latest
                    else None
                ),
                previous=(
                    previous.get("quality_score")
                    if previous
                    else None
                ),
                label="Quality score",
            )

            dependency_cmp = compare_metric(
                metric="dependency_score",
                current=(
                    latest.get("dependency_score")
                    if latest
                    else None
                ),
                previous=(
                    previous.get("dependency_score")
                    if previous
                    else None
                ),
                label="Dependency score",
            )

            pr_cmp = compare_metric(
                metric="pr_risk_score",
                current=(
                    latest.get("pr_risk_score")
                    if latest
                    else None
                ),
                previous=(
                    previous.get("pr_risk_score")
                    if previous
                    else None
                ),
                label="PR risk",
            )

            finding_latest = (
                (latest or {}).get("finding_counts") or {}
            )

            finding_previous = (
                (previous or {}).get("finding_counts") or {}
            )

            critical_cmp = compare_metric(
                metric="finding_critical",
                current=finding_latest.get("critical"),
                previous=finding_previous.get("critical"),
                label="Critical findings",
            )

            trend_direction = overall_trend_direction(
                [
                    health_cmp,
                    security_cmp,
                    quality_cmp,
                    dependency_cmp,
                    critical_cmp,
                ]
            )

            snapshot_count = (
                await self._snapshots.count_for_repository(
                    organization_id,
                    repo["id"],
                )
            )

            comparisons.append(
                AnalyticsRepositoryComparison(
                    id=repo["id"],
                    name=repo_names.get(
                        repo["id"],
                        "",
                    ),
                    health_score=(
                        latest.get("health_score")
                        if latest
                        else repo.get("health_score")
                    ),
                    security_score=(
                        latest.get("security_score")
                        if latest
                        else repo.get("security_score")
                    ),
                    quality_score=(
                        latest.get("quality_score")
                        if latest
                        else repo.get("code_quality_score")
                    ),
                    dependency_score=(
                        latest.get("dependency_score")
                        if latest
                        else repo.get("dependency_score")
                    ),
                    pr_risk_score=(
                        latest.get("pr_risk_score")
                        if latest
                        else None
                    ),
                    trend_direction=(
                        trend_direction
                        if previous
                        else "unavailable"
                    ),
                    last_analyzed_at=format_datetime(
                        repo.get("last_analyzed_at")
                    ),
                    last_snapshot_at=(
                        format_datetime(
                            latest.get("captured_at")
                        )
                        if latest
                        else None
                    ),
                    snapshot_count=snapshot_count,
                    health_comparison=self._to_change(
                        health_cmp,
                        repo,
                        latest,
                    ),
                    security_comparison=self._to_change(
                        security_cmp,
                        repo,
                        latest,
                    ),
                    quality_comparison=self._to_change(
                        quality_cmp,
                        repo,
                        latest,
                    ),
                    dependency_comparison=self._to_change(
                        dependency_cmp,
                        repo,
                        latest,
                    ),
                    critical_findings_comparison=self._to_change(
                        critical_cmp,
                        repo,
                        latest,
                    ),
                )
            )

        comparisons.sort(
            key=lambda row: (
                row.health_score is not None,
                row.health_score or 0,
            ),
            reverse=True,
        )

        return comparisons

    def _to_change(
        self,
        comparison: dict[str, Any],
        repo: dict[str, Any],
        latest: dict[str, Any] | None,
    ) -> HistoricalChange | None:
        if (
            not comparison.get("available")
            and comparison.get("current") is None
        ):
            return None

        return HistoricalChange(
            metric=comparison["metric"],
            label=comparison["label"],
            current=comparison.get("current"),
            previous=comparison.get("previous"),
            delta=comparison.get("delta"),
            percentage_change=comparison.get(
                "percentage_change"
            ),
            direction=comparison.get(
                "direction",
                "unavailable",
            ),
            interpretation=comparison.get(
                "interpretation",
                "",
            ),
            available=bool(
                comparison.get("available")
            ),
            repository_id=repo["id"],
            repository_name=(
                repo.get("full_name")
                or repo.get("name", "")
            ),
            detected_at=(
                format_datetime(
                    latest.get("captured_at")
                )
                if latest
                else None
            ),
        )

    def _detect_changes(
        self,
        comparisons: list[AnalyticsRepositoryComparison],
    ) -> tuple[
        list[HistoricalChange],
        list[HistoricalChange],
    ]:
        regressions: list[HistoricalChange] = []
        improvements: list[HistoricalChange] = []

        checks = [
            ("health_comparison", "health_score"),
            ("security_comparison", "security_score"),
            ("quality_comparison", "quality_score"),
            ("dependency_comparison", "dependency_score"),
            (
                "critical_findings_comparison",
                "finding_critical",
            ),
        ]

        for row in comparisons:
            for attr, metric in checks:
                change: HistoricalChange | None = getattr(
                    row,
                    attr,
                )

                if (
                    not change
                    or not change.available
                    or change.delta is None
                ):
                    continue

                if is_material_regression(
                    metric,
                    change.delta,
                ):
                    regressions.append(change)

                elif is_material_improvement(
                    metric,
                    change.delta,
                ):
                    improvements.append(change)

        return regressions[:12], improvements[:12]