from __future__ import annotations

import asyncio
import logging
from typing import Any


logger = logging.getLogger(__name__)


class PullRequestRiskService:
    """
    Service for calculating and persisting pull-request risk scores.

    Batch guarantees:
    - Open PRs are fetched once.
    - Repository findings are fetched once.
    - Previous average risk score is fetched once.
    - PR scoring runs concurrently.
    - Concurrency is bounded.
    - Failure of one PR does not abort the batch.
    """

    MAX_CONCURRENT_PRS = 5

    def __init__(
        self,
        pull_request_repository: Any,
        finding_repository: Any,
        repository_repository: Any,
    ) -> None:
        self.pull_request_repository = pull_request_repository
        self.finding_repository = finding_repository
        self.repository_repository = repository_repository

    async def score_open_pull_requests(
        self,
        *,
        organization_id: str,
        repository_id: str,
        owner: str,
        name: str,
        client: Any,
        repository_doc: dict[str, Any] | None = None,
    ) -> int:
        """
        Score all open pull requests for a repository.

        Returns the number of successfully scored pull requests.
        """

        # Fetch the open PR list once.
        pulls = await client.list_pull_requests(
            owner,
            name,
            state="open",
        )

        # Fetch batch-level data exactly once.
        repo_findings = await self.finding_repository.list_by_repository(
            repository_id,
            organization_id,
        )

        prior_average = (
            await self.pull_request_repository.average_risk_score(
                organization_id,
                repository_id=repository_id,
            )
        )

        if repository_doc is None:
            repository_doc = await self.repository_repository.get_by_id(
                repository_id,
                organization_id,
            )

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PRS)

        async def score_one(pr: dict[str, Any]) -> bool:
            async with semaphore:
                try:
                    number = pr.get("number")

                    if number is None:
                        raise ValueError(
                            "Pull request is missing its number"
                        )

                    # Detail and file retrieval are independent, so fetch
                    # them concurrently for this PR.
                    pr_detail_task = asyncio.create_task(
                        client.get_pull_request(
                            owner,
                            name,
                            number,
                        )
                    )

                    files_task = asyncio.create_task(
                        client.list_pull_request_files(
                            owner,
                            name,
                            number,
                        )
                    )

                    pr_detail, files = await asyncio.gather(
                        pr_detail_task,
                        files_task,
                    )

                    risk_score = self._calculate_risk_score(
                        pull_request=pr,
                        pull_request_detail=pr_detail,
                        files=files,
                        repo_findings=repo_findings,
                        prior_average=prior_average,
                        repository_doc=repository_doc,
                    )

                    github_id = pr.get("id")

                    if github_id is None:
                        github_id = pr_detail.get("id")

                    if github_id is None:
                        raise ValueError(
                            f"Pull request #{number} is missing github_id"
                        )

                    await self.pull_request_repository.update_risk_score(
                        github_id=github_id,
                        risk_score=risk_score,
                    )

                    return True

                except Exception:
                    logger.exception(
                        "Failed to score pull request #%s "
                        "for repository %s",
                        pr.get("number"),
                        repository_id,
                    )
                    return False

        results = await asyncio.gather(
            *(score_one(pr) for pr in pulls),
        )

        return sum(results)

    def _calculate_risk_score(
        self,
        *,
        pull_request: dict[str, Any],
        pull_request_detail: dict[str, Any],
        files: list[dict[str, Any]],
        repo_findings: list[Any],
        prior_average: float | None,
        repository_doc: dict[str, Any],
    ) -> float:
        """
        Calculate a deterministic 0-100 pull-request risk score.
        """

        score = 0.0

        # --------------------------------------------------------------
        # Number of changed files
        # --------------------------------------------------------------

        changed_files = len(files)

        if changed_files >= 20:
            score += 35
        elif changed_files >= 10:
            score += 25
        elif changed_files >= 5:
            score += 15
        elif changed_files >= 1:
            score += 5

        # --------------------------------------------------------------
        # Lines changed
        # --------------------------------------------------------------

        additions = sum(
            int(file.get("additions") or 0)
            for file in files
        )

        deletions = sum(
            int(file.get("deletions") or 0)
            for file in files
        )

        total_changes = additions + deletions

        if total_changes >= 1000:
            score += 30
        elif total_changes >= 500:
            score += 20
        elif total_changes >= 200:
            score += 12
        elif total_changes >= 50:
            score += 6

        # --------------------------------------------------------------
        # Existing findings
        # --------------------------------------------------------------

        finding_count = len(repo_findings)

        if finding_count >= 20:
            score += 20
        elif finding_count >= 10:
            score += 15
        elif finding_count >= 5:
            score += 10
        elif finding_count >= 1:
            score += 5

        # --------------------------------------------------------------
        # Repository risk level
        # --------------------------------------------------------------

        risk_level = str(
            repository_doc.get("risk_level", "low")
        ).lower()

        if risk_level == "critical":
            score += 20
        elif risk_level == "high":
            score += 15
        elif risk_level == "medium":
            score += 8

        # --------------------------------------------------------------
        # Previous average
        # --------------------------------------------------------------

        if prior_average is not None:
            try:
                average = float(prior_average)

                if average >= 80:
                    score += 10
                elif average >= 60:
                    score += 7
                elif average >= 40:
                    score += 4

            except (TypeError, ValueError):
                pass

        return round(
            max(0.0, min(score, 100.0)),
            2,
        )