from datetime import UTC, datetime
from typing import Any, Literal

from app.lib.dashboard_helpers import duration_seconds, format_datetime
from app.repositories.findings import FindingRepository
from app.repositories.analysis_runs import AnalysisRunRepository, CANCELLED_ERROR
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.analysis_runs import (
    AnalysisRunActionResponse,
    AnalysisRunCapabilities,
    AnalysisRunDetailResponse,
    AnalysisRunListItem,
    AnalysisRunSnapshotSummary,
    AnalyzerFailedItem,
    AnalyzerSkippedItem,
    AnalyzerSummary,
)
from app.schemas.pagination import PaginatedResponse
from app.services.repositories import RepositoryService


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def _is_commit_search(q: str) -> bool:
    stripped = q.strip()
    return len(stripped) >= 4 and all(c in "0123456789abcdefABCDEF" for c in stripped)


class AnalysisRunsService:
    def __init__(
        self,
        analysis_runs: AnalysisRunRepository,
        analysis_snapshots: AnalysisSnapshotRepository,
        repositories: RepositoryRepository,
        repository_service: RepositoryService,
        findings: FindingRepository,
    ) -> None:
        self._analysis_runs = analysis_runs
        self._analysis_snapshots = analysis_snapshots
        self._repositories = repositories
        self._repository_service = repository_service
        self._findings = findings

    async def _repo_name_map(self, organization_id: str) -> dict[str, str]:
        docs = await self._repositories.list_by_organization(organization_id)
        return {
            doc["id"]: doc.get("full_name") or doc.get("name", "Repository")
            for doc in docs
        }

    async def _resolve_repository_ids_for_search(
        self,
        organization_id: str,
        q: str,
    ) -> list[str] | None:
        if _is_commit_search(q):
            return None
        pattern = {"$regex": q.strip(), "$options": "i"}
        docs, _ = await self._repositories.list_by_organization_paginated(
            organization_id,
            skip=0,
            limit=500,
            q=q.strip(),
        )
        if not docs:
            return []
        return [doc["id"] for doc in docs]

    def _health_score_from_run(self, doc: dict[str, Any]) -> float | None:
        snapshot = doc.get("health_snapshot")
        if isinstance(snapshot, dict):
            score = snapshot.get("health_score")
            if isinstance(score, (int, float)):
                return float(score)
        return None

    def _to_list_item(self, doc: dict[str, Any], repo_names: dict[str, str]) -> AnalysisRunListItem:
        repo_id = str(doc.get("repository_id", ""))
        return AnalysisRunListItem(
            id=doc["id"],
            repository_id=repo_id,
            repository_name=repo_names.get(repo_id, "Repository"),
            status=str(doc.get("status", "queued")),
            trigger=str(doc.get("trigger", "")),
            trigger_source=doc.get("trigger_source"),
            commit_sha=doc.get("commit_sha"),
            branch=doc.get("branch"),
            started_at=format_datetime(doc.get("started_at")),
            completed_at=format_datetime(doc.get("completed_at")),
            duration_seconds=duration_seconds(doc.get("started_at"), doc.get("completed_at")),
            finding_count=int(doc.get("finding_count", 0)),
            health_score=self._health_score_from_run(doc),
            error=doc.get("error"),
            created_at=format_datetime(doc.get("created_at")),
        )

    def _parse_analyzer_summary(self, raw: Any) -> AnalyzerSummary | None:
        if not isinstance(raw, dict):
            return None
        skipped = [
            AnalyzerSkippedItem(name=str(item.get("name", "")), reason=str(item.get("reason", "")))
            for item in raw.get("skipped", [])
            if isinstance(item, dict)
        ]
        failed = [
            AnalyzerFailedItem(name=str(item.get("name", "")), reason=str(item.get("reason", "")))
            for item in raw.get("failed", [])
            if isinstance(item, dict)
        ]
        executed = [str(name) for name in raw.get("executed", []) if isinstance(name, str)]
        return AnalyzerSummary(
            executed=executed,
            skipped=skipped,
            failed=failed,
            dependency_scan=bool(raw.get("dependency_scan")),
        )

    def _capabilities(self, doc: dict[str, Any], role: str) -> AnalysisRunCapabilities:
        status = str(doc.get("status", ""))
        is_member = role in {"owner", "admin", "member"}
        can_retry = is_member and status == "failed" and doc.get("error") != CANCELLED_ERROR
        can_cancel = is_member and status == "queued"
        return AnalysisRunCapabilities(can_retry=can_retry, can_cancel=can_cancel)

    async def list_runs(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        repository_id: str | None = None,
        status: str | None = None,
        trigger: str | None = None,
        q: str | None = None,
        started_from: str | None = None,
        started_to: str | None = None,
        sort: Literal["started", "completed", "duration", "status"] = "started",
        order: Literal["asc", "desc"] = "desc",
    ) -> PaginatedResponse[AnalysisRunListItem]:
        repository_ids: list[str] | None = None
        commit_q: str | None = None
        if q and q.strip():
            if _is_commit_search(q):
                commit_q = q.strip()
            else:
                repository_ids = await self._resolve_repository_ids_for_search(organization_id, q)
                if repository_ids == []:
                    return PaginatedResponse.build([], total=0, page=page, page_size=page_size)

        skip = (page - 1) * page_size
        docs, total = await self._analysis_runs.list_for_organization_paginated(
            organization_id,
            skip=skip,
            limit=page_size,
            repository_id=repository_id,
            status=status,
            trigger=trigger,
            q=commit_q,
            repository_ids=repository_ids,
            started_from=_parse_datetime(started_from),
            started_to=_parse_datetime(started_to),
            sort=sort,
            order=order,
        )
        repo_names = await self._repo_name_map(organization_id)
        items = [self._to_list_item(doc, repo_names) for doc in docs]
        return PaginatedResponse.build(items, total=total, page=page, page_size=page_size)

    async def get_run_detail(
        self,
        analysis_id: str,
        organization_id: str,
        *,
        role: str,
    ) -> AnalysisRunDetailResponse | None:
        doc = await self._analysis_runs.get_by_id(analysis_id, organization_id)
        if not doc:
            return None

        repo_names = await self._repo_name_map(organization_id)
        repo_id = str(doc.get("repository_id", ""))
        repo_name = repo_names.get(repo_id, "Repository")
        base = self._to_list_item(doc, repo_names)

        findings_by_category: dict[str, int] | None = None
        if doc.get("status") == "complete":
            latest = await self._analysis_runs.latest_for_repository(repo_id, organization_id)
            if latest and latest.get("id") == analysis_id:
                findings = await self._findings.list_by_repository(repo_id, organization_id)
                findings_by_category = {}
                for finding in findings:
                    category = str(finding.get("category", "unknown"))
                    findings_by_category[category] = findings_by_category.get(category, 0) + 1

        snapshot_doc = await self._analysis_snapshots.get_by_analysis_run(
            analysis_run_id=analysis_id,
            organization_id=organization_id,
        )
        snapshot_summary: AnalysisRunSnapshotSummary | None = None
        analytics_href: str | None = None
        if snapshot_doc:
            snapshot_summary = AnalysisRunSnapshotSummary(
                id=snapshot_doc["id"],
                captured_at=format_datetime(snapshot_doc.get("captured_at")),
                health_score=snapshot_doc.get("health_score"),
                security_score=snapshot_doc.get("security_score"),
                quality_score=snapshot_doc.get("quality_score"),
                dependency_score=snapshot_doc.get("dependency_score"),
                pr_risk_score=snapshot_doc.get("pr_risk_score"),
            )
            analytics_href = f"/app/analytics?repositoryId={repo_id}"

        return AnalysisRunDetailResponse(
            id=base.id,
            repository_id=base.repository_id,
            repository_name=repo_name,
            status=base.status,
            trigger=base.trigger,
            trigger_source=base.trigger_source,
            commit_sha=base.commit_sha,
            branch=base.branch,
            started_at=base.started_at,
            completed_at=base.completed_at,
            duration_seconds=base.duration_seconds,
            finding_count=base.finding_count,
            error=base.error,
            created_at=base.created_at,
            analyzer_summary=self._parse_analyzer_summary(doc.get("analyzer_summary")),
            health_snapshot=doc.get("health_snapshot") if isinstance(doc.get("health_snapshot"), dict) else None,
            findings_by_category=findings_by_category,
            snapshot=snapshot_summary,
            capabilities=self._capabilities(doc, role),
            repository_href=f"/app/repositories/{repo_id}",
            analytics_href=analytics_href,
        )

    async def retry_run(
        self,
        analysis_id: str,
        organization_id: str,
    ) -> AnalysisRunActionResponse | None:
        doc = await self._analysis_runs.get_by_id(analysis_id, organization_id)
        if not doc:
            return None
        if doc.get("status") != "failed":
            raise ValueError("Only failed analysis runs can be retried.")
        if doc.get("error") == CANCELLED_ERROR:
            raise ValueError("Cancelled runs cannot be retried.")

        repository_id = str(doc.get("repository_id", ""))
        status_value = await self._repository_service.queue_analysis(
            repository_id,
            organization_id,
            trigger="retry",
        )
        if status_value is None:
            raise ValueError("Repository not found.")
        if status_value == "already_queued":
            raise ValueError("Analysis is already queued or running for this repository.")

        latest = await self._analysis_runs.latest_for_repository(repository_id, organization_id)
        return AnalysisRunActionResponse(
            status="queued",
            analysis_run_id=latest["id"] if latest else None,
            message="Analysis retry queued.",
        )

    async def cancel_run(
        self,
        analysis_id: str,
        organization_id: str,
    ) -> AnalysisRunActionResponse | None:
        doc = await self._analysis_runs.get_by_id(analysis_id, organization_id)
        if not doc:
            return None
        if doc.get("status") != "queued":
            raise ValueError("Only queued analysis runs can be cancelled.")

        cancelled = await self._analysis_runs.mark_cancelled(analysis_id, organization_id)
        if not cancelled:
            raise ValueError("Analysis run could not be cancelled.")

        repository_id = str(doc.get("repository_id", ""))
        await self._repositories.update_analysis_status(
            repository_id,
            organization_id,
            status="failed",
        )
        return AnalysisRunActionResponse(
            status="cancelled",
            analysis_run_id=analysis_id,
            message="Analysis run cancelled.",
        )
