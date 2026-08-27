import logging

from typing import Any

from app.core.config import get_settings
from app.lib.dashboard_helpers import duration_seconds
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.repository import (
    AnalysisRunResponse,
    PullRequestDetailResponse,
    PullRequestResponse,
    RepositoryResponse,
    RiskFactor,
    RiskScore,
)
from app.services.github_integration import GitHubIntegrationService


logger = logging.getLogger(__name__)


def _format_timestamp(value: Any) -> str | None:
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


class RepositoryService:
    def __init__(
        self,
        repositories: RepositoryRepository,
        pull_requests: PullRequestRepository,
        github: GitHubIntegrationService | None = None,
        analysis_runs: AnalysisRunRepository | None = None,
    ) -> None:
        self._repositories = repositories
        self._pull_requests = pull_requests
        self._github = github
        self._analysis_runs = analysis_runs

    # ------------------------------------------------------------------
    # Repository response
    # ------------------------------------------------------------------

    def to_repository_response(
        self,
        doc: dict[str, Any],
    ) -> RepositoryResponse:
        return RepositoryResponse(
            id=doc["id"],
            name=doc["name"],
            owner=doc.get("owner", ""),
            language=doc.get("language"),
            health_score=doc.get("health_score"),
            security_score=doc.get("security_score"),
            code_quality_score=doc.get("code_quality_score"),
            dependency_score=doc.get("dependency_score"),
            coverage_percent=doc.get("coverage_percent"),
            open_pull_requests=doc.get("open_pull_requests", 0),
            risk_level=doc.get("risk_level"),
            analysis_status=doc.get(
                "analysis_status",
                "not_started",
            ),
            last_analyzed_at=_format_timestamp(
                doc.get("last_analyzed_at")
            ),
            github_id=doc.get("github_id"),
            full_name=doc.get("full_name"),
            html_url=doc.get("html_url"),
            default_branch=doc.get("default_branch"),
            private=doc.get("private"),
            dependency_status=doc.get("dependency_status"),
            security_finding_count=doc.get(
                "security_finding_count"
            ),
            quality_finding_count=doc.get(
                "quality_finding_count"
            ),
        )

    # ------------------------------------------------------------------
    # Risk score
    # ------------------------------------------------------------------

    def to_risk_score(
        self,
        detail: Any,
    ) -> RiskScore | None:
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
                        label=str(
                            factor.get("label", "")
                        ),
                        contribution=int(
                            factor.get(
                                "contribution",
                                0,
                            )
                        ),
                        explanation=str(
                            factor.get(
                                "explanation",
                                "",
                            )
                        ),
                    )
                )

        value = detail.get(
            "value",
            detail.get("risk_score"),
        )

        if value is None:
            return None

        return RiskScore(
            value=int(value),
            level=detail.get("level", "low"),
            factors=factors,
            engine=str(
                detail.get(
                    "engine",
                    "Verion Risk Engine v1",
                )
            ),
        )

    # ------------------------------------------------------------------
    # Pull request response
    # ------------------------------------------------------------------

    def to_pull_request_response(
        self,
        doc: dict[str, Any],
    ) -> PullRequestResponse:
        return PullRequestResponse(
            id=int(doc["id"]),
            repository_id=doc.get(
                "repository_id",
                "",
            ),
            repository_name=doc.get(
                "repository_name",
                "",
            ),
            title=doc.get("title", ""),
            author=doc.get("author", ""),
            risk_score=doc.get("risk_score"),
            files_changed=doc.get(
                "files_changed",
                0,
            ),
            coverage_percent=doc.get(
                "coverage_percent"
            ),
            issues_count=doc.get(
                "issues_count",
                0,
            ),
            status=doc.get(
                "status",
                "open",
            ),
            created_at=_format_timestamp(
                doc.get("created_at")
            )
            or "",
        )

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    async def list_repositories(
        self,
        organization_id: str,
    ) -> list[RepositoryResponse]:
        page = await self.list_repositories_paginated(
            organization_id,
            page=1,
            page_size=10_000,
        )

        return page.items

    async def list_repositories_paginated(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        analysis_status: str | None = None,
        risk_level: str | None = None,
        security_status: str | None = None,
        sort: str = "name",
        order: str = "asc",
    ) -> PaginatedResponse[RepositoryResponse]:
        skip = (page - 1) * page_size

        docs, total = (
            await self._repositories.list_by_organization_paginated(
                organization_id,
                skip=skip,
                limit=page_size,
                q=q,
                analysis_status=analysis_status,
                risk_level=risk_level,
                security_status=security_status,
                sort=sort,
                order=order,
            )
        )

        items = [
            self.to_repository_response(doc)
            for doc in docs
        ]

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_repository(
        self,
        repository_id: str,
        organization_id: str,
    ) -> RepositoryResponse | None:
        doc = await self._repositories.get_by_id(
            repository_id,
            organization_id,
        )

        if not doc:
            return None

        return self.to_repository_response(doc)

    # ------------------------------------------------------------------
    # Connect repository
    # ------------------------------------------------------------------

    async def connect_repository(
        self,
        organization_id: str,
        github_id: int,
    ) -> RepositoryResponse:
        if not self._github:
            raise ValueError(
                "GitHub integration is unavailable."
            )

        # --------------------------------------------------------------
        # Prevent duplicate repository connections.
        # --------------------------------------------------------------

        existing = (
            await self._repositories.get_by_github_id(
                github_id,
                organization_id,
            )
        )

        if existing:
            return self.to_repository_response(existing)

        # --------------------------------------------------------------
        # Get GitHub client and available repositories.
        # --------------------------------------------------------------

        client = await self._github.get_github_client(
            organization_id
        )

        options = (
            await self._github.list_available_repositories(
                organization_id
            )
        )

        selected = next(
            (
                repo
                for repo in options
                if repo.github_id == github_id
            ),
            None,
        )

        if not selected:
            raise ValueError(
                "Repository not found in your GitHub account."
            )

        # --------------------------------------------------------------
        # Get current repository information from GitHub.
        # --------------------------------------------------------------

        remote = await client.get_repository(
            selected.owner,
            selected.name,
        )

        webhook_id: int | None = None
        settings = get_settings()

        # --------------------------------------------------------------
        # Create GitHub webhook.
        #
        # GitHub cannot reach localhost.
        #
        # PUBLIC_URL must contain the externally reachable URL.
        #
        # Example:
        #
        # PUBLIC_URL=https://abc123.trycloudflare.com
        #
        # Callback:
        #
        # https://abc123.trycloudflare.com/api/v1/webhooks/github
        # --------------------------------------------------------------

        if settings.github_webhook_secret:
            public_url = (
                settings.public_url
                .strip()
                .rstrip("/")
            )

            if not public_url:
                raise ValueError(
                    "PUBLIC_URL is required when "
                    "GITHUB_WEBHOOK_SECRET is configured. "
                    "GitHub webhooks cannot use localhost."
                )

            callback_url = (
                f"{public_url}/api/v1/webhooks/github"
            )

            hook = await client.create_repository_webhook(
                selected.owner,
                selected.name,
                callback_url=callback_url,
                secret=settings.github_webhook_secret,
            )

            hook_id_value = hook.get("id")

            webhook_id = (
                hook_id_value
                if isinstance(hook_id_value, int)
                else None
            )

            logger.info(
                "Created GitHub webhook for %s/%s: %s",
                selected.owner,
                selected.name,
                callback_url,
            )

        # --------------------------------------------------------------
        # Save repository.
        # --------------------------------------------------------------

        doc = await self._repositories.create(
            organization_id=organization_id,
            github_id=github_id,
            name=selected.name,
            owner=selected.owner,
            full_name=selected.full_name,
            language=remote.get("language"),
            default_branch=remote.get(
                "default_branch"
            ),
            html_url=remote.get("html_url"),
            private=bool(
                remote.get(
                    "private",
                    False,
                )
            ),
            webhook_id=webhook_id,
        )

        # --------------------------------------------------------------
        # Queue initial repository analysis.
        # --------------------------------------------------------------

        await self.queue_analysis(
            doc["id"],
            organization_id,
            trigger="connect",
        )

        return self.to_repository_response(doc)

    # ------------------------------------------------------------------
    # Disconnect repository
    # ------------------------------------------------------------------

    async def disconnect_repository(
        self,
        repository_id: str,
        organization_id: str,
    ) -> bool:
        doc = await self._repositories.delete(
            repository_id,
            organization_id,
        )

        if not doc:
            return False

        # --------------------------------------------------------------
        # Delete GitHub webhook if one exists.
        # --------------------------------------------------------------

        if (
            self._github
            and doc.get("webhook_id")
            and doc.get("owner")
            and doc.get("name")
        ):
            try:
                client = (
                    await self._github.get_github_client(
                        organization_id
                    )
                )

                await client.delete_repository_webhook(
                    doc["owner"],
                    doc["name"],
                    int(doc["webhook_id"]),
                )

            except Exception:
                logger.warning(
                    "Failed to delete GitHub webhook %s "
                    "for %s/%s",
                    doc.get("webhook_id"),
                    doc.get("owner"),
                    doc.get("name"),
                    exc_info=True,
                )

        return True

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    async def queue_analysis(
        self,
        repository_id: str,
        organization_id: str,
        *,
        trigger: str = "manual",
    ) -> str | None:
        doc = await self._repositories.get_by_id(
            repository_id,
            organization_id,
        )

        if not doc:
            return None

        if self._analysis_runs is None:
            raise RuntimeError(
                "Analysis run repository is unavailable."
            )

        # --------------------------------------------------------------
        # Prevent duplicate active analyses.
        # --------------------------------------------------------------

        if await self._repositories.has_active_analysis(
            repository_id,
            organization_id,
        ):
            return "already_queued"

        if (
            await self._analysis_runs.has_active_for_repository(
                repository_id,
                organization_id,
            )
        ):
            return "already_queued"

        # --------------------------------------------------------------
        # Create analysis run.
        # --------------------------------------------------------------

        run = await self._analysis_runs.create(
            repository_id=repository_id,
            organization_id=organization_id,
            trigger=trigger,
            status="queued",
        )

        await self._repositories.update_analysis_status(
            repository_id,
            organization_id,
            status="queued",
        )

        # Import here to avoid circular imports.
        from app.workers.tasks.analysis import (
            enqueue_analysis,
        )

        enqueue_analysis(
            repository_id,
            organization_id,
            trigger=trigger,
            analysis_run_id=run["id"],
        )

        return "queued"

    # ------------------------------------------------------------------
    # Pull requests
    # ------------------------------------------------------------------

    async def list_pull_requests(
        self,
        organization_id: str,
    ) -> list[PullRequestResponse]:
        page = await self.list_pull_requests_paginated(
            organization_id,
            page=1,
            page_size=10_000,
        )

        return page.items

    async def list_pull_requests_paginated(
        self,
        organization_id: str,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[PullRequestResponse]:
        skip = (page - 1) * page_size

        docs, total = (
            await self._pull_requests.list_by_organization_paginated(
                organization_id,
                skip=skip,
                limit=page_size,
            )
        )

        items = [
            self.to_pull_request_response(doc)
            for doc in docs
        ]

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Analysis run response
    # ------------------------------------------------------------------

    def to_analysis_run_response(
        self,
        doc: dict[str, Any],
    ) -> AnalysisRunResponse:
        health_score = None

        health_snapshot = doc.get(
            "health_snapshot"
        )

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

        return AnalysisRunResponse(
            id=doc["id"],
            repository_id=doc.get(
                "repository_id",
                "",
            ),
            status=doc.get(
                "status",
                "queued",
            ),
            trigger=doc.get(
                "trigger",
                "",
            ),
            trigger_source=doc.get(
                "trigger_source"
            ),
            commit_sha=doc.get(
                "commit_sha"
            ),
            branch=doc.get(
                "branch"
            ),
            started_at=_format_timestamp(
                doc.get("started_at")
            ),
            completed_at=_format_timestamp(
                doc.get("completed_at")
            ),
            duration_seconds=duration_seconds(
                doc.get("started_at"),
                doc.get("completed_at"),
            ),
            finding_count=int(
                doc.get(
                    "finding_count",
                    0,
                )
            ),
            error=doc.get("error"),
            created_at=_format_timestamp(
                doc.get("created_at")
            ),
            health_score=health_score,
        )

    # ------------------------------------------------------------------
    # Analysis runs
    # ------------------------------------------------------------------

    async def list_analysis_runs_paginated(
        self,
        repository_id: str,
        organization_id: str,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[AnalysisRunResponse] | None:
        if self._analysis_runs is None:
            return PaginatedResponse.build(
                [],
                total=0,
                page=page,
                page_size=page_size,
            )

        repo = await self._repositories.get_by_id(
            repository_id,
            organization_id,
        )

        if not repo:
            return None

        skip = (page - 1) * page_size

        docs, total = (
            await self._analysis_runs.list_by_repository_paginated(
                repository_id=repository_id,
                organization_id=organization_id,
                skip=skip,
                limit=page_size,
            )
        )

        items = [
            self.to_analysis_run_response(doc)
            for doc in docs
        ]

        return PaginatedResponse.build(
            items,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Pull request detail
    # ------------------------------------------------------------------

    async def get_pull_request(
        self,
        pr_id: int,
        organization_id: str,
    ) -> PullRequestDetailResponse | None:
        doc = (
            await self._pull_requests.get_by_github_id(
                pr_id,
                organization_id,
            )
        )

        if not doc:
            return None

        base = self.to_pull_request_response(doc)

        return PullRequestDetailResponse(
            **base.model_dump(),
            risk_score_detail=self.to_risk_score(
                doc.get(
                    "risk_score_detail"
                )
            ),
            description=doc.get(
                "description"
            ),
        )

    # ------------------------------------------------------------------
    # Pull request risk
    # ------------------------------------------------------------------

    async def get_pull_request_risk(
        self,
        pr_id: int,
        organization_id: str,
    ) -> RiskScore | None:
        doc = (
            await self._pull_requests.get_by_github_id(
                pr_id,
                organization_id,
            )
        )

        if not doc:
            return None

        return self.to_risk_score(
            doc.get(
                "risk_score_detail"
            )
        )