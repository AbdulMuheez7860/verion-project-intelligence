from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.analyzers.bandit import BanditAnalyzer
from app.analyzers.base import AnalyzerFinding, AnalyzerResult
from app.analyzers.dependencies import DependencyAnalyzer
from app.analyzers.eslint import EslintAnalyzer
from app.analyzers.repository_metrics import (
    RepositoryMetrics,
    compute_repository_metrics,
)
from app.analyzers.ruff import RuffAnalyzer
from app.analyzers.secrets import SecretDetectionAnalyzer
from app.analyzers.semgrep import SemgrepAnalyzer


class AnalysisOrchestrator:
    """
    Coordinates all repository analyzers.

    The orchestrator has one critical responsibility:

    An analyzer returning zero findings is NOT the same thing as an
    analyzer failing.

    Example:

        completed + 0 findings
            -> repository was successfully checked and nothing was found

        failed + 0 findings
            -> repository was NOT fully checked

    The second case must never be treated as a clean repository.
    """

    def __init__(
        self,
        analyzers: list | None = None,
        *,
        max_workers: int = 5,
    ) -> None:
        # NOTE: DependencyAnalyzer is deliberately NOT included here.
        # Dependency scanning has its own return shape (findings AND
        # dependency records) and is executed exactly once, via
        # run_dependency_scan(). It used to also be registered here,
        # which caused every analysis run to execute the dependency
        # scan twice and required the caller to filter out the
        # duplicate "pip-audit" findings after the fact. Do not add it
        # back to this list.
        self._analyzers = analyzers or [
            SemgrepAnalyzer(),
            BanditAnalyzer(),
            RuffAnalyzer(),
            EslintAnalyzer(),
            SecretDetectionAnalyzer(),
        ]

        # These analyzers are independent of one another (each only
        # reads the cloned workspace and shells out to its own
        # subprocess), so they are safe to run concurrently. They are
        # I/O/process-bound rather than CPU-bound in this process, so a
        # thread pool is used instead of multiprocessing to avoid the
        # cost of forking/pickling for what is mostly "wait for a
        # subprocess" work.
        self._max_workers = max(1, max_workers)

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Backwards-compatible simple execution method.

        Returns findings from analyzers that completed successfully.

        IMPORTANT:
        For production analysis-status decisions, use
        run_with_execution_log() instead because this method intentionally
        does not expose analyzer failures.
        """

        findings, _ = self.run_with_execution_log(workspace)
        return findings

    def run_with_execution_log(
        self,
        workspace: Path,
    ) -> tuple[list[AnalyzerFinding], dict[str, Any]]:
        """
        Execute all applicable analyzers and return normalized findings
        together with a complete execution report.

        The execution report explicitly distinguishes:

        - completed
        - skipped
        - failed
        - total analyzers
        - successful analyzers
        - failed analyzers
        - skipped analyzers
        - finding count
        - overall analysis status

        This prevents scanner failures from being interpreted as
        "zero findings".
        """

        workspace = Path(workspace)

        if not workspace.exists():
            raise FileNotFoundError(
                f"Analysis workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise NotADirectoryError(
                f"Analysis workspace is not a directory: {workspace}"
            )

        # -------------------------------------------------------------
        # Determine which analyzers actually apply to this repository.
        #
        # supports() is treated as cheap/best-effort (glob checks, file
        # existence) and is run up front, sequentially, so we know the
        # exact set of analyzers to schedule concurrently below.
        # -------------------------------------------------------------
        skipped: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        runnable: list[tuple[Any, str]] = []

        for analyzer in self._analyzers:
            name = getattr(
                analyzer,
                "name",
                analyzer.__class__.__name__,
            )

            try:
                supported = analyzer.supports(workspace)
            except Exception as exc:
                failed.append(
                    {
                        "name": name,
                        "status": "failed",
                        "error_code": "SUPPORT_CHECK_FAILED",
                        "reason": self._safe_error_message(exc),
                    }
                )
                continue

            if not supported:
                skipped.append(
                    {
                        "name": name,
                        "status": "skipped",
                        "reason": "Unsupported for this repository",
                    }
                )
                continue

            runnable.append((analyzer, name))

        # -------------------------------------------------------------
        # Execute all applicable analyzers concurrently.
        #
        # Each analyzer only reads the shared workspace and shells out
        # to its own subprocess (bandit, ruff, semgrep, eslint,
        # detect-secrets), so there is no shared mutable state between
        # them and running them in parallel cannot change the result,
        # only how long it takes to get it.
        #
        # IMPORTANT:
        # An empty list is a SUCCESS if the analyzer completed.
        # Exceptions are recorded as FAILURE.
        # -------------------------------------------------------------
        results_by_name: dict[str, dict[str, Any]] = {}
        findings_by_name: dict[str, list[AnalyzerFinding]] = {}

        def _execute(
            analyzer: Any,
            name: str,
        ) -> tuple[str, list[AnalyzerFinding] | None, dict[str, Any]]:
            try:
                analyzer_findings = analyzer.run(workspace)

                if analyzer_findings is None:
                    raise RuntimeError(
                        f"{name} returned None instead of a list of findings"
                    )

                if not isinstance(analyzer_findings, list):
                    raise TypeError(
                        f"{name} returned "
                        f"{type(analyzer_findings).__name__} "
                        "instead of list[AnalyzerFinding]"
                    )

                return (
                    name,
                    analyzer_findings,
                    {
                        "name": name,
                        "status": "completed",
                        "finding_count": len(analyzer_findings),
                    },
                )

            except TimeoutError as exc:
                return (
                    name,
                    None,
                    {
                        "name": name,
                        "status": "timeout",
                        "error_code": "ANALYZER_TIMEOUT",
                        "reason": self._safe_error_message(exc),
                    },
                )

            except Exception as exc:
                return (
                    name,
                    None,
                    {
                        "name": name,
                        "status": "failed",
                        "error_code": "ANALYZER_EXECUTION_FAILED",
                        "reason": self._safe_error_message(exc),
                    },
                )

        if runnable:
            with ThreadPoolExecutor(
                max_workers=min(self._max_workers, len(runnable))
            ) as pool:
                futures = [
                    pool.submit(_execute, analyzer, name)
                    for analyzer, name in runnable
                ]

                for future in as_completed(futures):
                    name, analyzer_findings, log_entry = future.result()
                    results_by_name[name] = log_entry

                    if analyzer_findings is not None:
                        findings_by_name[name] = analyzer_findings

        # Re-assemble results in the original analyzer order so output
        # (and any downstream consumer relying on ordering) stays
        # deterministic regardless of which thread finished first.
        findings: list[AnalyzerFinding] = []
        completed: list[dict[str, Any]] = []

        for _analyzer, name in runnable:
            log_entry = results_by_name[name]

            if log_entry["status"] == "completed":
                completed.append(log_entry)
                findings.extend(findings_by_name.get(name, []))
            else:
                failed.append(log_entry)

        execution_log = self._build_execution_log(
            total=len(self._analyzers),
            completed=completed,
            skipped=skipped,
            failed=failed,
            finding_count=len(findings),
        )

        return findings, execution_log

    def run_dependency_scan(
        self,
        workspace: Path,
    ) -> tuple[list[AnalyzerFinding], list, dict[str, Any]]:
        """
        Execute the dependency analyzer separately.

        Dependency scanning is kept separate because the dependency
        analyzer returns both normalized findings and dependency records.

        A failed dependency scan is explicitly reported as failed and
        MUST NOT be interpreted as "no vulnerable dependencies".
        """

        workspace = Path(workspace)

        if not workspace.exists():
            raise FileNotFoundError(
                f"Dependency analysis workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise NotADirectoryError(
                f"Dependency analysis workspace is not a directory: {workspace}"
            )

        analyzer = DependencyAnalyzer()

        name = getattr(
            analyzer,
            "name",
            analyzer.__class__.__name__,
        )

        # -------------------------------------------------------------
        # Check dependency manifest support.
        # -------------------------------------------------------------
        try:
            supported = analyzer.supports(workspace)
        except Exception as exc:
            return [], [], {
                "status": "failed",
                "executed": False,
                "completed": [],
                "skipped": [],
                "failed": [
                    {
                        "name": name,
                        "status": "failed",
                        "error_code": "SUPPORT_CHECK_FAILED",
                        "reason": self._safe_error_message(exc),
                    }
                ],
                "finding_count": 0,
            }

        if not supported:
            return [], [], {
                "status": "skipped",
                "executed": False,
                "completed": [],
                "skipped": [
                    {
                        "name": name,
                        "status": "skipped",
                        "reason": "No supported dependency manifest found",
                    }
                ],
                "failed": [],
                "finding_count": 0,
            }

        # -------------------------------------------------------------
        # Execute dependency scanner.
        # -------------------------------------------------------------
        try:
            dep_findings, dep_records = analyzer.scan(workspace)

            if dep_findings is None:
                raise RuntimeError(
                    f"{name} returned None for dependency findings"
                )

            if dep_records is None:
                raise RuntimeError(
                    f"{name} returned None for dependency records"
                )

            result = {
                "status": "completed",
                "executed": True,
                "completed": [
                    {
                        "name": name,
                        "status": "completed",
                        "finding_count": len(dep_findings),
                        "dependency_count": len(dep_records),
                    }
                ],
                "skipped": [],
                "failed": [],
                "finding_count": len(dep_findings),
                "dependency_count": len(dep_records),
            }

            return dep_findings, dep_records, result

        except TimeoutError as exc:
            return [], [], {
                "status": "failed",
                "executed": False,
                "completed": [],
                "skipped": [],
                "failed": [
                    {
                        "name": name,
                        "status": "timeout",
                        "error_code": "ANALYZER_TIMEOUT",
                        "reason": self._safe_error_message(exc),
                    }
                ],
                "finding_count": 0,
            }

        except Exception as exc:
            return [], [], {
                "status": "failed",
                "executed": False,
                "completed": [],
                "skipped": [],
                "failed": [
                    {
                        "name": name,
                        "status": "failed",
                        "error_code": "ANALYZER_EXECUTION_FAILED",
                        "reason": self._safe_error_message(exc),
                    }
                ],
                "finding_count": 0,
            }

    @staticmethod
    def _build_execution_log(
        *,
        total: int,
        completed: list[dict[str, Any]],
        skipped: list[dict[str, Any]],
        failed: list[dict[str, Any]],
        finding_count: int,
    ) -> dict[str, Any]:
        """
        Build the canonical analyzer execution report.

        Overall status rules:

        COMPLETE
            Every applicable analyzer completed successfully.

        PARTIAL
            At least one analyzer completed and at least one analyzer
            failed, OR some analyzers were skipped while the applicable
            analyzers completed.

        FAILED
            No analyzer completed successfully and at least one analyzer
            failed.

        The distinction matters because "0 findings" is only trustworthy
        when the relevant analyzers actually completed.
        """

        completed_count = len(completed)
        skipped_count = len(skipped)
        failed_count = len(failed)

        if failed_count == 0:
            status = "completed"
        elif completed_count > 0:
            status = "partial"
        else:
            status = "failed"

        return {
            "status": status,
            "total": total,
            "executed": [item["name"] for item in completed],
            "completed": completed,
            "skipped": skipped,
            "failed": failed,
            "executed_count": completed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "finding_count": finding_count,
            "analysis_complete": status == "completed",
        }

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        """
        Return a bounded error message suitable for logs/API responses.

        Avoid exposing massive subprocess output or sensitive environment
        information through the execution log.
        """

        message = str(exc).strip()

        if not message:
            message = exc.__class__.__name__

        return message[:500]

    def run_repository_metrics(
        self,
        workspace: Path,
    ) -> tuple[RepositoryMetrics | None, dict[str, Any]]:
        """
        Compute repository/LOC/language metrics.

        This is a local, dependency-free computation (no subprocess, no
        network), so it has no UNAVAILABLE state the way an external
        tool would - it either completes or raises. A failure here is
        always FAILED, never silently converted into zero files.
        """

        workspace = Path(workspace)

        if not workspace.exists() or not workspace.is_dir():
            return None, {
                "status": "failed",
                "error_code": "WORKSPACE_MISSING",
                "reason": "Analysis workspace does not exist.",
            }

        try:
            metrics = compute_repository_metrics(workspace)
        except Exception as exc:
            return None, {
                "status": "failed",
                "error_code": "REPOSITORY_METRICS_FAILED",
                "reason": self._safe_error_message(exc),
            }

        return metrics, {
            "status": "completed",
            "total_files": metrics.total_files,
            "truncated": metrics.truncated,
        }