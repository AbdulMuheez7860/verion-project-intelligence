from datetime import UTC, datetime
from typing import Any

from app.lib.historical_helpers import (
    breakdown_from_severity_counts,
    severity_breakdown_from_findings,
)
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository


class AnalysisSnapshotService:
    def __init__(self, snapshots: AnalysisSnapshotRepository) -> None:
        self._snapshots = snapshots

    async def create_from_analysis(
        self,
        *,
        organization_id: str,
        repository_id: str,
        analysis_run_id: str,
        commit_sha: str | None,
        branch: str | None,
        captured_at: datetime | None,
        health_score: float,
        security_score: float,
        quality_score: float,
        dependency_score: float,
        pr_risk_score: float | None,
        stored_findings: list[dict[str, Any]],
        dep_counts: dict[str, int],
        pull_request_metrics: dict[str, Any],
        analyzer_summary: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        security_findings = severity_breakdown_from_findings(
            stored_findings,
            categories={"security", "secret"},
        )

        quality_findings = severity_breakdown_from_findings(
            stored_findings,
            categories={"quality"},
        )

        dependency_findings = severity_breakdown_from_findings(
            stored_findings,
            categories={"dependency"},
        )

        finding_counts = {
            "total": (
                security_findings["total"]
                + quality_findings["total"]
                + dependency_findings["total"]
            ),
            "critical": (
                security_findings["critical"]
                + quality_findings["critical"]
                + dependency_findings["critical"]
            ),
            "high": (
                security_findings["high"]
                + quality_findings["high"]
                + dependency_findings["high"]
            ),
            "medium": (
                security_findings["medium"]
                + quality_findings["medium"]
                + dependency_findings["medium"]
            ),
            "low": (
                security_findings["low"]
                + quality_findings["low"]
                + dependency_findings["low"]
            ),
        }

        now = captured_at or datetime.now(UTC)

        payload = {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "analysis_run_id": analysis_run_id,
            "commit_sha": commit_sha,
            "branch": branch,
            "captured_at": now,
            "health_score": health_score,
            "security_score": security_score,
            "quality_score": quality_score,
            "dependency_score": dependency_score,
            "pr_risk_score": pr_risk_score,
            "finding_counts": finding_counts,
            "security_findings": security_findings,
            "quality_findings": quality_findings,
            "dependency_findings": dependency_findings,
            "dependency_counts": dep_counts,
            "pull_request_metrics": pull_request_metrics,
            "analyzer_summary": analyzer_summary,
        }

        return await self._snapshots.create_snapshot(payload)

    async def create_from_health_snapshot(
        self,
        *,
        organization_id: str,
        repository_id: str,
        analysis_run_id: str,
        commit_sha: str | None,
        branch: str | None,
        completed_at: datetime | None,
        health_snapshot: dict[str, Any],
        analyzer_summary: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Backfill-safe creation from legacy analysis_runs.health_snapshot only."""

        if not health_snapshot:
            return None

        severity_counts = health_snapshot.get("severity_counts")

        if not isinstance(severity_counts, dict):
            return None

        finding_counts = breakdown_from_severity_counts(severity_counts)
        captured_at = completed_at or datetime.now(UTC)

        payload = {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "analysis_run_id": analysis_run_id,
            "commit_sha": commit_sha,
            "branch": branch,
            "captured_at": captured_at,
            "health_score": health_snapshot.get("health_score"),
            "security_score": health_snapshot.get("security_score"),
            "quality_score": health_snapshot.get("code_quality_score"),
            "dependency_score": health_snapshot.get("dependency_score"),
            "pr_risk_score": None,
            "finding_counts": finding_counts,
            "security_findings": None,
            "quality_findings": None,
            "dependency_findings": None,
            "dependency_counts": None,
            "pull_request_metrics": None,
            "analyzer_summary": analyzer_summary,
        }

        return await self._snapshots.create_snapshot(payload)