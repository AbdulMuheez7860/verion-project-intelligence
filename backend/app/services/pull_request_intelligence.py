from typing import Any

from app.lib.dashboard_helpers import format_datetime, pr_risk_level, pr_verdict
from app.lib.pr_helpers import (
    build_pr_freshness,
    build_pr_recommendations,
    categorize_changed_file,
    derive_affected_areas,
    merge_safety_label,
    verdict_fields,
)
from app.repositories.findings import FindingRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.findings import QualityFindingResponse, SecurityFindingResponse, SeverityCounts
from app.schemas.pagination import PaginatedResponse
from app.schemas.pull_request_intelligence import (
    AffectedArea,
    ChangedFileItem,
    MergeSafetyVerdict,
    PRAnalysisInfo,
    PRFreshness,
    PRImpactCounts,
    PRRecommendation,
    PullRequestIntelligenceResponse,
    PullRequestListItem,
    RepositoryHealthContext,
)
from app.schemas.repository import RiskFactor, RiskScore
from app.services.findings import FindingsService
from app.services.pr_risk_engine import filter_findings_for_changed_files


class PullRequestIntelligenceService:
    def __init__(
        self,
        pull_requests: PullRequestRepository,
        findings: FindingRepository,
        repositories: RepositoryRepository,
        findings_service: FindingsService,
    ) -> None:
        self._pull_requests = pull_requests
        self._findings = findings
        self._repositories = repositories
        self._findings_service = findings_service

    def _to_list_item(self, doc: dict[str, Any]) -> PullRequestListItem:
        verdict_key, verdict_label, _ = verdict_fields(doc.get("risk_score"))
        if doc.get("verdict"):
            verdict_key = str(doc["verdict"])
            _, verdict_label, _ = pr_verdict(doc.get("risk_score"))
        return PullRequestListItem(
            id=int(doc["id"]),
            number=doc.get("number"),
            repository_id=doc.get("repository_id", ""),
            repository_name=doc.get("repository_name", ""),
            title=doc.get("title", ""),
            author=doc.get("author", ""),
            status=doc.get("status", "open"),
            draft=bool(doc.get("draft", False)),
            risk_score=doc.get("risk_score"),
            risk_level=doc.get("risk_level") or pr_risk_level(doc.get("risk_score")),
            verdict=verdict_key,
            verdict_label=verdict_label,
            security_impact=int(doc.get("security_issues_count", 0)),
            quality_impact=int(doc.get("quality_issues_count", 0)),
            dependency_impact=int(doc.get("dependency_issues_count", 0)),
            files_changed=int(doc.get("files_changed", 0)),
            issues_count=int(doc.get("issues_count", 0)),
            risk_scored_at=format_datetime(doc.get("risk_scored_at")),
            updated_at=format_datetime(doc.get("updated_at")),
            created_at=format_datetime(doc.get("created_at")) or "",
            html_url=doc.get("html_url"),
        )

    async def list_pull_requests_paginated(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        repository_id: str | None = None,
        status: str | None = None,
        risk_level: str | None = None,
        verdict: str | None = None,
        author: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
    ) -> PaginatedResponse[PullRequestListItem]:
        skip = (page - 1) * page_size
        docs, total = await self._pull_requests.list_by_organization_paginated(
            organization_id,
            skip=skip,
            limit=page_size,
            q=q,
            repository_id=repository_id,
            status=status,
            risk_level=risk_level,
            verdict=verdict,
            author=author,
            sort=sort,
            order=order,
        )
        items = [self._to_list_item(doc) for doc in docs]
        return PaginatedResponse.build(items, total=total, page=page, page_size=page_size)

    def _to_risk_score(self, doc: dict[str, Any]) -> RiskScore | None:
        detail = doc.get("risk_score_detail")
        if not isinstance(detail, dict):
            return None
        factors_raw = detail.get("factors", [])
        factors: list[RiskFactor] = []
        if isinstance(factors_raw, list):
            for factor in factors_raw:
                if not isinstance(factor, dict):
                    continue
                factors.append(
                    RiskFactor(
                        label=str(factor.get("label", "")),
                        contribution=int(factor.get("contribution", 0)),
                        explanation=str(factor.get("explanation", "")),
                    ),
                )
        value = detail.get("value", doc.get("risk_score"))
        if value is None:
            return None
        return RiskScore(
            value=int(value),
            level=detail.get("level", pr_risk_level(int(value)) or "low"),
            factors=factors,
            engine=str(detail.get("engine", "Verion Risk Engine v1")),
        )

    async def get_intelligence(
        self,
        github_id: int,
        organization_id: str,
    ) -> PullRequestIntelligenceResponse | None:
        doc = await self._pull_requests.get_by_github_id(github_id, organization_id)
        if not doc:
            return None

        repository_doc = None
        repository_id = doc.get("repository_id")
        if repository_id:
            repository_doc = await self._repositories.get_by_id(repository_id, organization_id)

        changed_files_raw = doc.get("changed_files", [])
        if not isinstance(changed_files_raw, list):
            changed_files_raw = []
        changed_files = [str(path) for path in changed_files_raw]

        file_details_raw = doc.get("file_details", [])
        if not isinstance(file_details_raw, list):
            file_details_raw = []
        if file_details_raw:
            changed_file_items = [
                ChangedFileItem(
                    path=str(item.get("path", "")),
                    status=str(item.get("status", "modified")),
                    additions=int(item.get("additions", 0)),
                    deletions=int(item.get("deletions", 0)),
                    category=item.get("category"),
                )
                for item in file_details_raw
                if isinstance(item, dict) and item.get("path")
            ]
        else:
            changed_file_items = [
                ChangedFileItem(
                    path=path,
                    status="modified",
                    category=categorize_changed_file(path),
                )
                for path in changed_files
            ]

        repo_findings: list[dict[str, Any]] = []
        if repository_id:
            repo_findings = await self._findings.list_by_repository(repository_id, organization_id)
        matched = filter_findings_for_changed_files(repo_findings, changed_files)
        repo_names = {
            repository_id: (repository_doc or {}).get("full_name") or doc.get("repository_name", ""),
        } if repository_id else {}

        security_docs = [f for f in matched if f.get("category") in {"security", "secret", "dependency"}]
        quality_docs = [f for f in matched if f.get("category") == "quality"]
        dependency_docs = [f for f in matched if f.get("category") == "dependency"]

        security_findings = [self._findings_service._to_security_finding(f, repo_names) for f in security_docs]
        quality_findings = [self._findings_service._to_quality_finding(f, repo_names) for f in quality_docs]
        dependency_findings = [self._findings_service._to_security_finding(f, repo_names) for f in dependency_docs]

        severity_counts = SeverityCounts()
        for finding in security_docs + dependency_docs:
            severity = str(finding.get("severity", "low"))
            if severity == "critical":
                severity_counts.critical += 1
            elif severity == "high":
                severity_counts.high += 1
            elif severity == "medium":
                severity_counts.medium += 1
            else:
                severity_counts.low += 1

        verdict_key, verdict_label, verdict_reason = verdict_fields(doc.get("risk_score"))
        if doc.get("verdict"):
            verdict_key = str(doc["verdict"])
            _, verdict_label, verdict_reason = pr_verdict(doc.get("risk_score"))

        freshness_data = build_pr_freshness(
            risk_scored_at=doc.get("risk_scored_at"),
            pr_updated_at=doc.get("updated_at"),
            repository_last_analyzed_at=(repository_doc or {}).get("last_analyzed_at"),
            repository_analysis_status=(repository_doc or {}).get("analysis_status"),
            risk_score=doc.get("risk_score"),
        )

        recommendations = build_pr_recommendations(
            verdict_key=verdict_key,
            freshness=freshness_data,
            security_findings=security_docs,
            quality_findings=quality_docs,
            dependency_findings=dependency_docs,
            changed_files=[item.model_dump() for item in changed_file_items],
            repository_analysis_status=(repository_doc or {}).get("analysis_status"),
        )

        affected = derive_affected_areas(changed_files, matched)

        repository_health = None
        if repository_doc:
            repository_health = RepositoryHealthContext(
                repository_id=repository_doc["id"],
                repository_name=repository_doc.get("full_name") or repository_doc.get("name", ""),
                health_score=repository_doc.get("health_score"),
                security_score=repository_doc.get("security_score"),
                code_quality_score=repository_doc.get("code_quality_score"),
                risk_level=repository_doc.get("risk_level"),
                analysis_status=repository_doc.get("analysis_status", "not_started"),
                last_analyzed_at=format_datetime(repository_doc.get("last_analyzed_at")),
            )

        analysis_status = "complete" if doc.get("risk_score") is not None else "unavailable"
        if (repository_doc or {}).get("analysis_status") in {"queued", "running"}:
            analysis_status = str((repository_doc or {}).get("analysis_status"))

        return PullRequestIntelligenceResponse(
            id=int(doc["id"]),
            number=doc.get("number"),
            title=doc.get("title", ""),
            repository_id=doc.get("repository_id", ""),
            repository_name=doc.get("repository_name", ""),
            author=doc.get("author", ""),
            status=doc.get("status", "open"),
            draft=bool(doc.get("draft", False)),
            description=doc.get("description"),
            html_url=doc.get("html_url"),
            created_at=format_datetime(doc.get("created_at")) or "",
            updated_at=format_datetime(doc.get("updated_at")),
            merge_safety=MergeSafetyVerdict(
                key=verdict_key,
                label=merge_safety_label(verdict_key),
                headline=verdict_label,
                explanation=verdict_reason,
                risk_score=doc.get("risk_score"),
                risk_level=doc.get("risk_level") or pr_risk_level(doc.get("risk_score")),
            ),
            freshness=PRFreshness(**freshness_data),
            risk_score_detail=self._to_risk_score(doc),
            security_summary=severity_counts,
            security_findings=security_findings,
            quality_findings=quality_findings,
            dependency_findings=dependency_findings,
            impact_counts=PRImpactCounts(
                security=len(security_docs),
                quality=len(quality_docs),
                dependency=len(dependency_docs),
                total=len(matched),
            ),
            changed_files=changed_file_items,
            affected_areas=[AffectedArea(**area) for area in affected],
            repository_health=repository_health,
            analysis=PRAnalysisInfo(
                status=analysis_status,
                repository_analysis_status=(repository_doc or {}).get("analysis_status"),
                risk_scored_at=format_datetime(doc.get("risk_scored_at")),
                head_sha=doc.get("head_sha"),
                base_sha=doc.get("base_sha"),
            ),
            recommendations=[PRRecommendation(**item) for item in recommendations],
        )
