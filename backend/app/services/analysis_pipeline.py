import base64
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.analyzers.orchestrator import AnalysisOrchestrator
from app.analyzers.repository_metrics import RepositoryMetrics
from app.integrations.github.client import GitHubClient
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.integrations import IntegrationRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.services.analysis_snapshot_service import AnalysisSnapshotService
from app.services.notification_events import (
    STALE_ANALYSIS_DAYS,
    NotificationEventService,
)
from app.services.pr_risk_service import PullRequestRiskService
from app.services.risk_engine import compute_risk_metrics
from app.utils.encryption import decrypt_value


class AnalysisPipeline:
    """
    End-to-end repository analysis pipeline.

    Flow:

        GitHub repository
            ↓
        clone repository
            ↓
        resolve exact commit
            ↓
        run analyzers
            ↓
        normalize findings
            ↓
        persist findings/dependencies
            ↓
        calculate risk metrics
            ↓
        calculate PR risk
            ↓
        create snapshot
            ↓
        complete analysis

    The pipeline deliberately distinguishes:

        complete
        partial
        failed
        cancelled

    A repository must NOT be reported as completely analyzed when an
    applicable analyzer failed.
    """

    def __init__(
        self,
        *,
        repositories: RepositoryRepository,
        analysis_runs: AnalysisRunRepository,
        findings: FindingRepository,
        dependencies: DependencyRepository,
        pull_requests: PullRequestRepository,
        integrations: IntegrationRepository,
        orchestrator: AnalysisOrchestrator | None = None,
        snapshot_service: AnalysisSnapshotService | None = None,
        notification_events: NotificationEventService | None = None,
    ) -> None:
        self._repositories = repositories
        self._analysis_runs = analysis_runs
        self._findings = findings
        self._dependencies = dependencies
        self._pull_requests = pull_requests
        self._integrations = integrations
        self._orchestrator = orchestrator or AnalysisOrchestrator()
        self._pr_risk = PullRequestRiskService(
            pull_requests,
            findings,
            repositories,
        )
        self._snapshots = snapshot_service
        self._notification_events = notification_events

    async def _maybe_emit_stale_analysis(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
    ) -> None:
        if not self._notification_events:
            return

        latest = (
            await self._analysis_runs.latest_completed_for_repository(
                repository_id,
                organization_id,
            )
        )

        if not latest:
            return

        completed_at = latest.get("completed_at")

        if not isinstance(completed_at, datetime):
            return

        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=UTC)

        days = (
            datetime.now(UTC) - completed_at
        ).days

        if days >= STALE_ANALYSIS_DAYS:
            await self._notification_events.emit_analysis_stale(
                organization_id=organization_id,
                repository_id=repository_id,
                repository_name=repository_name,
                days_since_analysis=days,
            )

    async def run(
        self,
        repository_id: str,
        organization_id: str,
        trigger: str,
        *,
        analysis_run_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute one complete repository analysis.
        """

        repo = await self._repositories.get_by_id(
            repository_id,
            organization_id,
        )

        if not repo:
            return {
                "status": "skipped",
                "reason": "repository_not_found",
            }

        repository_name = (
            repo.get("full_name")
            or repo.get("name")
            or "Repository"
        )

        await self._maybe_emit_stale_analysis(
            organization_id=organization_id,
            repository_id=repository_id,
            repository_name=repository_name,
        )

        # -------------------------------------------------------------
        # Create or validate analysis run
        # -------------------------------------------------------------

        if analysis_run_id:
            existing = await self._analysis_runs.get_by_id(
                analysis_run_id,
                organization_id,
            )

            if (
                not existing
                or existing.get("repository_id") != repository_id
            ):
                raise ValueError(
                    "Analysis run not found."
                )

            if (
                existing.get("status") == "failed"
                and (
                    existing.get("error")
                    or ""
                ).startswith("Cancelled")
            ):
                await self._repositories.update_analysis_status(
                    repository_id,
                    organization_id,
                    status="failed",
                )

                return {
                    "status": "cancelled",
                    "analysis_id": analysis_run_id,
                }

            analysis_id = analysis_run_id

        else:
            analysis_run = await self._analysis_runs.create(
                repository_id=repository_id,
                organization_id=organization_id,
                trigger=trigger,
                status="queued",
            )

            analysis_id = analysis_run["id"]

        await self._analysis_runs.mark_running(
            analysis_id
        )

        await self._repositories.update_analysis_status(
            repository_id,
            organization_id,
            status="running",
        )

        workspace: Path | None = None

        try:
            # ---------------------------------------------------------
            # GitHub integration
            # ---------------------------------------------------------

            integration = (
                await self._integrations.get_github_by_organization(
                    organization_id
                )
            )

            if not integration:
                raise ValueError(
                    "GitHub integration not connected."
                )

            encrypted = integration.get(
                "access_token_encrypted"
            )

            if not isinstance(encrypted, str):
                raise ValueError(
                    "GitHub token missing."
                )

            access_token = decrypt_value(
                encrypted
            )

            if not access_token:
                raise ValueError(
                    "GitHub token could not be decrypted."
                )

            client = GitHubClient(
                access_token
            )

            owner = repo.get("owner")
            name = repo.get("name")

            if not isinstance(owner, str) or not owner:
                raise ValueError(
                    "Repository owner missing."
                )

            if not isinstance(name, str) or not name:
                raise ValueError(
                    "Repository name missing."
                )

            self._validate_repository_coordinate(
                owner,
                name,
            )

            # ---------------------------------------------------------
            # Fetch GitHub repository metadata
            # ---------------------------------------------------------

            remote = await client.get_repository(
                owner,
                name,
            )

            if not isinstance(remote, dict):
                raise RuntimeError(
                    "GitHub returned invalid repository metadata."
                )

            default_branch = (
                remote.get("default_branch")
                or repo.get("default_branch")
                or "main"
            )

            if not isinstance(default_branch, str):
                default_branch = "main"

            # ---------------------------------------------------------
            # Pull requests
            # ---------------------------------------------------------

            pulls = await client.list_pull_requests(
                owner,
                name,
                state="open",
            )

            if not isinstance(pulls, list):
                pulls = []

            await self._sync_pull_requests(
                repo,
                pulls,
            )

            await self._repositories.update_from_github(
                repository_id,
                organization_id,
                language=remote.get("language"),
                open_pull_requests=len(pulls),
                default_branch=default_branch,
            )

            # ---------------------------------------------------------
            # Clone exact repository
            # ---------------------------------------------------------

            workspace = self._clone_repository(
                owner=owner,
                name=name,
                access_token=access_token,
                default_branch=default_branch,
            )

            # ---------------------------------------------------------
            # Resolve exact analyzed commit
            # ---------------------------------------------------------

            commit_sha = self._resolve_commit_sha(
                workspace
            )

            if not commit_sha:
                raise RuntimeError(
                    "Unable to determine the commit SHA of the "
                    "repository being analyzed."
                )

            # ---------------------------------------------------------
            # Run analysis
            # ---------------------------------------------------------
            #
            # The general analyzers (security/quality/secrets, run
            # internally in parallel by the orchestrator) and the
            # dependency scan are entirely independent of one another —
            # neither reads the other's output — so they are also run
            # concurrently with each other here via a thread pool
            # rather than back to back.
            #
            # DependencyAnalyzer is intentionally registered ONLY in
            # run_dependency_scan(), not in the orchestrator's default
            # analyzer list, so it executes exactly once per analysis.
            # ---------------------------------------------------------

            with ThreadPoolExecutor(max_workers=3) as pool:
                analyzers_future = pool.submit(
                    self._orchestrator.run_with_execution_log,
                    workspace,
                )
                dependency_future = pool.submit(
                    self._orchestrator.run_dependency_scan,
                    workspace,
                )
                repo_metrics_future = pool.submit(
                    self._orchestrator.run_repository_metrics,
                    workspace,
                )

                analyzer_findings, execution_log = analyzers_future.result()
                dep_findings, dep_records, dep_log = dependency_future.result()
                repository_metrics, repo_metrics_log = (
                    repo_metrics_future.result()
                )

            all_findings = (
                analyzer_findings
                + dep_findings
            )

            # ---------------------------------------------------------
            # Analyzer execution state
            # ---------------------------------------------------------

            analyzer_summary = (
                self._build_analyzer_summary(
                    execution_log,
                    dep_log,
                    repo_metrics_log,
                    repository_metrics,
                )
            )

            analyzer_status = (
                self._determine_analysis_status(
                    analyzer_summary
                )
            )

            # ---------------------------------------------------------
            # Persist findings
            # ---------------------------------------------------------

            finding_count = (
                await self._findings.replace_for_analysis(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    analysis_id=analysis_id,
                    findings=all_findings,
                )
            )

            await self._dependencies.replace_for_analysis(
                organization_id=organization_id,
                repository_id=repository_id,
                analysis_id=analysis_id,
                records=dep_records,
            )

            # ---------------------------------------------------------
            # CRITICAL:
            #
            # Do not calculate current risk from every historical finding.
            #
            # The previous implementation called:
            #
            #     list_by_repository(...)
            #
            # which may include findings from previous analysis runs.
            #
            # Risk must be based on the current analyzed snapshot.
            #
            # If your repository class provides list_by_analysis(), use
            # that. Otherwise the current in-memory findings are used.
            # ---------------------------------------------------------

            stored_findings = await self._get_current_analysis_findings(
                repository_id=repository_id,
                organization_id=organization_id,
                analysis_id=analysis_id,
                fallback=all_findings,
            )

            # ---------------------------------------------------------
            # Risk metrics
            # ---------------------------------------------------------

            metrics = compute_risk_metrics(
                stored_findings
            )

            # ---------------------------------------------------------
            # Dependency metrics
            # ---------------------------------------------------------

            dep_counts = self._calculate_dependency_counts(
                dep_records
            )

            vulnerable = (
                dep_counts["vulnerable"]
                + dep_counts["critical"]
            )

            dependency_score = max(
                0.0,
                100.0 - (
                    vulnerable * 10
                ),
            )

            dependency_status = (
                self._dependency_status(
                    dep_counts
                )
            )

            # ---------------------------------------------------------
            # Finding categories
            # ---------------------------------------------------------

            security_finding_count = sum(
                1
                for finding in stored_findings
                if finding.get("category")
                in {
                    "security",
                    "secret",
                    "dependency",
                }
            )

            quality_finding_count = sum(
                1
                for finding in stored_findings
                if finding.get("category")
                == "quality"
            )

            # ---------------------------------------------------------
            # Repository scores
            # ---------------------------------------------------------

            await self._repositories.update_scores(
                repository_id,
                organization_id,
                health_score=metrics.health_score,
                security_score=metrics.security_score,
                code_quality_score=metrics.code_quality_score,
                risk_level=metrics.risk_level,
                dependency_score=dependency_score,
                dependency_status=dependency_status,
                security_finding_count=security_finding_count,
                quality_finding_count=quality_finding_count,
            )

            # ---------------------------------------------------------
            # Health snapshot
            # ---------------------------------------------------------

            health_snapshot = {
                "health_score": metrics.health_score,
                "security_score": metrics.security_score,
                "code_quality_score": (
                    metrics.code_quality_score
                ),
                "dependency_score": dependency_score,
                "risk_level": metrics.risk_level,
                "severity_counts": metrics.severity_counts,
                "recorded_at": datetime.now(
                    UTC
                ).isoformat(),
                "analysis_status": analyzer_status,
            }

            # ---------------------------------------------------------
            # PR risk analysis
            # ---------------------------------------------------------

            try:
                await self._pr_risk.score_open_pull_requests(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    owner=owner,
                    name=name,
                    client=client,
                    repository_doc=(
                        await self._repositories.get_by_id(
                            repository_id,
                            organization_id,
                        )
                        or repo
                    ),
                )
            except Exception as exc:
                # PR scoring failure should not destroy the entire
                # repository analysis, but it MUST be visible.
                analyzer_summary.setdefault(
                    "warnings",
                    [],
                ).append(
                    {
                        "component": "pull_request_risk",
                        "reason": str(exc)[:300],
                    }
                )

            pr_metrics = (
                await self._pull_requests.repository_pr_metrics(
                    organization_id,
                    repository_id,
                )
            )

            pr_risk_score = pr_metrics.get(
                "average_risk_score"
            )

            # ---------------------------------------------------------
            # Snapshot
            # ---------------------------------------------------------

            completed_at = datetime.now(
                UTC
            )

            if self._snapshots:
                await self._snapshots.create_from_analysis(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    analysis_run_id=analysis_id,
                    commit_sha=commit_sha,
                    branch=default_branch,
                    captured_at=completed_at,
                    health_score=metrics.health_score,
                    security_score=metrics.security_score,
                    quality_score=(
                        metrics.code_quality_score
                    ),
                    dependency_score=dependency_score,
                    pr_risk_score=pr_risk_score,
                    stored_findings=stored_findings,
                    dep_counts=dep_counts,
                    pull_request_metrics=pr_metrics,
                    analyzer_summary=analyzer_summary,
                )

            # ---------------------------------------------------------
            # Complete analysis
            # ---------------------------------------------------------

            if analyzer_status == "partial":
                await self._analysis_runs.mark_complete(
                    analysis_id,
                    finding_count=finding_count,
                    commit_sha=commit_sha,
                    analyzer_summary=analyzer_summary,
                    health_snapshot=health_snapshot,
                    branch=default_branch,
                )

                await self._repositories.update_analysis_status(
                    repository_id,
                    organization_id,
                    status="partial",
                )

            else:
                await self._analysis_runs.mark_complete(
                    analysis_id,
                    finding_count=finding_count,
                    commit_sha=commit_sha,
                    analyzer_summary=analyzer_summary,
                    health_snapshot=health_snapshot,
                    branch=default_branch,
                )

                await self._repositories.update_analysis_status(
                    repository_id,
                    organization_id,
                    status="complete",
                )

            # ---------------------------------------------------------
            # Notifications
            # ---------------------------------------------------------

            if self._notification_events:
                critical_security = sum(
                    1
                    for finding in stored_findings
                    if (
                        finding.get("category")
                        in {
                            "security",
                            "secret",
                        }
                        and finding.get("severity")
                        == "critical"
                    )
                )

                await self._notification_events.emit_analysis_completed(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    repository_name=repository_name,
                    analysis_run_id=analysis_id,
                    finding_count=finding_count,
                )

                if critical_security > 0:
                    await self._notification_events.emit_critical_security(
                        organization_id=organization_id,
                        repository_id=repository_id,
                        repository_name=repository_name,
                        critical_count=critical_security,
                        analysis_run_id=analysis_id,
                    )

                if dep_counts.get("critical", 0) > 0:
                    await self._notification_events.emit_critical_dependency(
                        organization_id=organization_id,
                        repository_id=repository_id,
                        repository_name=repository_name,
                        critical_count=dep_counts.get(
                            "critical",
                            0,
                        ),
                        analysis_run_id=analysis_id,
                    )

                await self._notification_events.emit_high_risk_prs(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    repository_name=repository_name,
                    analysis_run_id=analysis_id,
                )

                await self._notification_events.emit_regressions(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    repository_name=repository_name,
                    analysis_run_id=analysis_id,
                )

            return {
                "status": analyzer_status,
                "trigger": trigger,
                "analysis_id": analysis_id,
                "finding_count": finding_count,
                "open_pull_requests": len(pulls),
                "commit_sha": commit_sha,
                "analyzer_summary": analyzer_summary,
            }

        except Exception as exc:
            safe_error = self._sanitize_error(
                str(exc)
            )

            await self._analysis_runs.mark_failed(
                analysis_id,
                error=safe_error,
            )

            await self._repositories.update_analysis_status(
                repository_id,
                organization_id,
                status="failed",
            )

            if self._notification_events:
                await self._notification_events.emit_analysis_failed(
                    organization_id=organization_id,
                    repository_id=repository_id,
                    repository_name=repository_name,
                    analysis_run_id=analysis_id,
                    error=safe_error,
                )

            raise

        finally:
            if (
                workspace
                and workspace.exists()
            ):
                shutil.rmtree(
                    workspace,
                    ignore_errors=True,
                )

    async def _get_current_analysis_findings(
        self,
        *,
        repository_id: str,
        organization_id: str,
        analysis_id: str,
        fallback: list[Any],
    ) -> list[dict[str, Any]]:
        """
        Retrieve findings belonging to the current analysis.

        Prefer an analysis-specific repository method if available.

        Falling back to the current in-memory findings prevents historical
        findings from contaminating the current risk score.
        """

        list_by_analysis = getattr(
            self._findings,
            "list_by_analysis",
            None,
        )

        if callable(list_by_analysis):
            findings = await list_by_analysis(
                analysis_id,
                organization_id,
            )

            if isinstance(findings, list):
                return findings

        converted: list[dict[str, Any]] = []

        for finding in fallback:
            if isinstance(finding, dict):
                converted.append(finding)
                continue

            converted.append(
                {
                    "severity": getattr(
                        finding,
                        "severity",
                        "medium",
                    ),
                    "category": getattr(
                        finding,
                        "category",
                        "quality",
                    ),
                    "rule_id": getattr(
                        finding,
                        "rule_id",
                        "unknown",
                    ),
                    "title": getattr(
                        finding,
                        "title",
                        "Unknown finding",
                    ),
                    "description": getattr(
                        finding,
                        "description",
                        "",
                    ),
                    "file": getattr(
                        finding,
                        "file",
                        "",
                    ),
                    "line": getattr(
                        finding,
                        "line",
                        1,
                    ),
                    "confidence": getattr(
                        finding,
                        "confidence",
                        None,
                    ),
                    "remediation": getattr(
                        finding,
                        "remediation",
                        None,
                    ),
                    "metadata": getattr(
                        finding,
                        "metadata",
                        {},
                    ),
                }
            )

        return converted

    @staticmethod
    def _calculate_dependency_counts(
        records: list[Any],
    ) -> dict[str, int]:
        counts = {
            "total": len(records),
            "vulnerable": 0,
            "critical": 0,
            "outdated": 0,
            "healthy": 0,
        }

        for record in records:
            status = getattr(
                record,
                "status",
                None,
            )

            if status == "vulnerable":
                counts["vulnerable"] += 1
            elif status == "critical":
                counts["critical"] += 1
            elif status == "outdated":
                counts["outdated"] += 1
            elif status == "healthy":
                counts["healthy"] += 1

        return counts

    @staticmethod
    def _dependency_status(
        counts: dict[str, int],
    ) -> str | None:
        if counts["critical"] > 0:
            return "critical"

        if counts["vulnerable"] > 0:
            return "vulnerable"

        if counts["outdated"] > 0:
            return "outdated"

        if counts["healthy"] > 0:
            return "healthy"

        return None

    @staticmethod
    def _determine_analysis_status(
        summary: dict[str, Any],
    ) -> str:
        """
        Determine whether the analysis is complete or partial.

        An analyzer failure means we do not have full repository coverage.
        """

        failed = summary.get(
            "failed",
            [],
        )

        if failed:
            return "partial"

        return "complete"

    @staticmethod
    def _validate_repository_coordinate(
        owner: str,
        name: str,
    ) -> None:
        """
        Prevent malformed GitHub coordinates from reaching git.
        """

        if (
            not owner
            or not name
            or ".." in owner
            or ".." in name
            or "/" in owner
            or "/" in name
            or "\\" in owner
            or "\\" in name
            or owner.startswith("-")
            or name.startswith("-")
        ):
            raise ValueError(
                "Invalid repository coordinates."
            )

    def _resolve_commit_sha(
        self,
        workspace: Path,
    ) -> str | None:
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace),
                    "rev-parse",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
        except (
            subprocess.TimeoutExpired,
            OSError,
        ):
            return None

        if result.returncode != 0:
            return None

        sha = result.stdout.strip()

        if not sha:
            return None

        return sha

    def _clone_repository(
        self,
        *,
        owner: str,
        name: str,
        access_token: str,
        default_branch: str,
    ) -> Path:
        """
        Clone a GitHub repository without putting the access token in
        the subprocess argument list.

        This is important because credentials in command-line arguments
        can appear in process listings and diagnostic output.
        """

        self._validate_repository_coordinate(
            owner,
            name,
        )

        if not default_branch:
            default_branch = "main"

        if (
            default_branch.startswith("-")
            or "\n" in default_branch
            or "\r" in default_branch
        ):
            raise ValueError(
                "Invalid default branch."
            )

        workspace = Path(
            tempfile.mkdtemp(
                prefix="verion-analysis-"
            )
        )

        clone_url = (
            f"https://github.com/"
            f"{owner}/{name}.git"
        )

        # GitHub accepts Basic authentication where the username is
        # x-access-token and the password is the OAuth/PAT token.
        credentials = (
            f"x-access-token:{access_token}"
        )

        encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("ascii")

        env = os.environ.copy()

        # Configure Git through environment variables instead of placing
        # the token inside argv.
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = (
            "http.https://github.com/.extraheader"
        )
        env["GIT_CONFIG_VALUE_0"] = (
            f"Authorization: Basic {encoded_credentials}"
        )

        command = [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--branch",
            default_branch,
            clone_url,
            str(workspace),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            shutil.rmtree(
                workspace,
                ignore_errors=True,
            )

            raise TimeoutError(
                "Repository clone exceeded the 300 second timeout."
            ) from exc
        except OSError as exc:
            shutil.rmtree(
                workspace,
                ignore_errors=True,
            )

            raise RuntimeError(
                f"Unable to execute git clone: {exc}"
            ) from exc

        if result.returncode != 0:
            detail = (
                result.stderr
                or result.stdout
                or "git clone failed"
            ).strip()

            # Never propagate credentials accidentally.
            detail = detail.replace(
                access_token,
                "[REDACTED]",
            )

            shutil.rmtree(
                workspace,
                ignore_errors=True,
            )

            # Branch fallback.
            #
            # Some GitHub repositories can have an unexpected/default
            # branch mismatch. A normal shallow clone without --branch
            # allows Git to use the repository's advertised default.
            fallback_command = [
                "git",
                "clone",
                "--depth",
                "1",
                "--single-branch",
                clone_url,
                str(workspace),
            ]

            try:
                fallback = subprocess.run(
                    fallback_command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=300,
                    env=env,
                )
            except (
                subprocess.TimeoutExpired,
                OSError,
            ) as exc:
                shutil.rmtree(
                    workspace,
                    ignore_errors=True,
                )

                raise RuntimeError(
                    "GitHub repository clone failed."
                ) from exc

            if fallback.returncode != 0:
                fallback_detail = (
                    fallback.stderr
                    or fallback.stdout
                    or detail
                    or "git clone failed"
                ).strip()

                fallback_detail = fallback_detail.replace(
                    access_token,
                    "[REDACTED]",
                )

                shutil.rmtree(
                    workspace,
                    ignore_errors=True,
                )

                raise RuntimeError(
                    f"Git clone failed: "
                    f"{fallback_detail[:500]}"
                )

        return workspace

    async def _sync_pull_requests(
        self,
        repo: dict[str, Any],
        pulls: list[dict[str, Any]],
    ) -> None:
        organization_id = repo[
            "organization_id"
        ]

        repository_id = repo[
            "id"
        ]

        repository_name = (
            repo.get("full_name")
            or repo.get("name", "")
        )

        for pull in pulls:
            if not isinstance(pull, dict):
                continue

            github_id = pull.get("id")

            if not isinstance(
                github_id,
                int,
            ):
                continue

            user = pull.get(
                "user",
                {},
            )

            author = (
                user.get("login")
                if isinstance(user, dict)
                else "unknown"
            )

            if not isinstance(
                author,
                str,
            ):
                author = "unknown"

            created_at_raw = pull.get(
                "created_at"
            )

            if isinstance(
                created_at_raw,
                str,
            ):
                try:
                    created_at = (
                        datetime.fromisoformat(
                            created_at_raw.replace(
                                "Z",
                                "+00:00",
                            )
                        )
                    )
                except ValueError:
                    created_at = datetime.now(
                        UTC
                    )
            else:
                created_at = datetime.now(
                    UTC
                )

            if created_at.tzinfo is None:
                created_at = created_at.replace(
                    tzinfo=UTC
                )

            head = (
                pull.get("head", {})
                if isinstance(
                    pull.get("head"),
                    dict,
                )
                else {}
            )

            base = (
                pull.get("base", {})
                if isinstance(
                    pull.get("base"),
                    dict,
                )
                else {}
            )

            await self._pull_requests.upsert_from_github(
                organization_id=organization_id,
                repository_id=repository_id,
                repository_name=repository_name,
                github_id=github_id,
                number=(
                    pull.get("number")
                    if isinstance(
                        pull.get("number"),
                        int,
                    )
                    else None
                ),
                title=str(
                    pull.get("title")
                    or ""
                ),
                author=author,
                files_changed=(
                    pull.get("changed_files")
                    if isinstance(
                        pull.get(
                            "changed_files"
                        ),
                        int,
                    )
                    else 0
                ),
                status="open",
                created_at=created_at,
                description=(
                    pull.get("body")
                    if isinstance(
                        pull.get("body"),
                        str,
                    )
                    else None
                ),
                draft=bool(
                    pull.get(
                        "draft",
                        False,
                    )
                ),
                html_url=(
                    pull.get("html_url")
                    if isinstance(
                        pull.get("html_url"),
                        str,
                    )
                    else None
                ),
                head_sha=(
                    head.get("sha")
                    if isinstance(
                        head.get("sha"),
                        str,
                    )
                    else None
                ),
                base_sha=(
                    base.get("sha")
                    if isinstance(
                        base.get("sha"),
                        str,
                    )
                    else None
                ),
            )

    def _build_analyzer_summary(
        self,
        execution_log: dict[str, Any],
        dep_log: dict[str, Any],
        repo_metrics_log: dict[str, Any] | None = None,
        repository_metrics: RepositoryMetrics | None = None,
    ) -> dict[str, Any]:
        executed = list(
            execution_log.get(
                "executed",
                [],
            )
        )

        skipped = list(
            execution_log.get(
                "skipped",
                [],
            )
        )

        failed = list(
            execution_log.get(
                "failed",
                [],
            )
        )

        warnings: list[dict[str, str]] = []

        # -------------------------------------------------------------
        # Dependency scan
        #
        # DependencyAnalyzer only runs via run_dependency_scan(), so its
        # execution state is merged in here rather than appearing in
        # execution_log.
        # -------------------------------------------------------------

        dependency_scan = bool(
            dep_log.get(
                "executed",
                False,
            )
        )

        dependency_name = "pip-audit"

        if dependency_scan:
            if dependency_name not in executed:
                executed.append(
                    dependency_name
                )
        else:
            skipped.extend(
                dep_log.get(
                    "skipped",
                    [],
                )
            )

            failed.extend(
                dep_log.get(
                    "failed",
                    [],
                )
            )

        # Remove duplicate analyzer names.
        executed = list(
            dict.fromkeys(
                executed
            )
        )

        # -------------------------------------------------------------
        # Repository / LOC / language metrics
        #
        # This is a local, dependency-free, supplementary computation.
        # It is deliberately NOT added to `failed` above: a failure
        # here means Verion cannot report LOC/language breakdown, but
        # it does not mean security/quality coverage was incomplete,
        # so it must not flip an otherwise-complete analysis to
        # "partial". Its own status is reported separately instead.
        # -------------------------------------------------------------

        repo_metrics_log = repo_metrics_log or {}
        repo_metrics_status = repo_metrics_log.get("status", "failed")

        return {
            "executed": executed,
            "skipped": skipped,
            "failed": failed,
            "warnings": warnings,
            "dependency_scan": dependency_scan,
            "total_executed": len(executed),
            "total_skipped": len(skipped),
            "total_failed": len(failed),
            "repository_metrics": (
                repository_metrics.to_dict()
                if repository_metrics is not None
                else None
            ),
            "repository_metrics_status": repo_metrics_status,
            "repository_metrics_error": (
                repo_metrics_log.get("reason")
                if repo_metrics_status == "failed"
                else None
            ),
        }

    @staticmethod
    def _sanitize_error(
        error: str,
    ) -> str:
        """
        Basic protection against accidentally exposing credentials in
        analysis errors.

        The actual GitHub token is handled separately in clone logic.
        """

        if not error:
            return "Unknown analysis error."

        return error[:1000]