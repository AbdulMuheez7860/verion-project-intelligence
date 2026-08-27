import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerFinding, normalize_severity
from app.analyzers.normalize import first_int, relative_path, truncate


class RuffAnalyzer:
    name = "ruff"

    def supports(self, workspace: Path) -> bool:
        """
        Ruff is applicable when the repository contains Python files.
        """
        return any(workspace.rglob("*.py"))

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Execute Ruff and normalize its JSON output.

        Important:
        - Empty stdout is NOT automatically considered success.
        - Ruff's return code must be inspected.
        - Ruff returns exit code 1 when findings are present.
        - Ruff returns exit code 0 when no findings exist.
        - Any other non-zero exit code is treated as analyzer failure.
        """

        executable = shutil.which("ruff")

        if executable is None:
            raise RuntimeError(
                "Ruff executable was not found in PATH. "
                "Install Ruff or configure the analyzer environment."
            )

        try:
            result = subprocess.run(
                [
                    executable,
                    "check",
                    str(workspace),
                    "--output-format",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Ruff analysis exceeded the 120 second timeout."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Failed to start Ruff: {exc}"
            ) from exc

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Ruff:
        #   0 = no violations
        #   1 = violations found
        #   other = execution/configuration failure
        if result.returncode not in (0, 1):
            error_details = stderr or stdout or "Unknown Ruff error."

            raise RuntimeError(
                f"Ruff failed with exit code {result.returncode}: "
                f"{truncate(error_details, 500)}"
            )

        # Exit code 0 with no output is a legitimate clean result.
        if result.returncode == 0 and not stdout:
            return []

        # Exit code 1 should contain JSON findings.
        if not stdout:
            raise RuntimeError(
                "Ruff reported violations but produced no JSON output."
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Ruff returned invalid JSON output."
            ) from exc

        if not isinstance(payload, list):
            raise RuntimeError(
                "Ruff returned an unexpected JSON structure. "
                "Expected a list of findings."
            )

        return parse_ruff_results(payload, str(workspace))


def parse_ruff_results(
    payload: list[dict[str, Any]],
    workspace_root: str,
) -> list[AnalyzerFinding]:
    """
    Convert Ruff's native JSON findings into Verion's normalized format.
    """

    findings: list[AnalyzerFinding] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        code = str(item.get("code") or "ruff.unknown").strip()

        message = truncate(
            str(item.get("message") or code).strip()
        )

        location = item.get("location")

        line = 1
        column = 1
        file_path = ""

        if isinstance(location, dict):
            line = first_int(location.get("row"))

            raw_column = location.get("column")

            try:
                column = int(raw_column)
            except (TypeError, ValueError):
                column = 1

            raw_filename = str(
                location.get("filename") or ""
            )

            if raw_filename:
                file_path = relative_path(
                    raw_filename,
                    workspace_root,
                )

        # -------------------------------------------------------------
        # Ruff fixability MUST NOT determine severity.
        #
        # The previous implementation did:
        #
        #     severity = "high" if str(item.get("fix", "")) else ...
        #
        # This was incorrect because:
        #
        #     str(None) == "None"
        #
        # and "None" is truthy.
        #
        # Therefore findings with no fix could incorrectly become HIGH.
        #
        # Fixability and severity are independent concepts.
        # -------------------------------------------------------------

        severity = ruff_severity(code)

        fix = item.get("fix")

        fix_available = isinstance(fix, dict)

        remediation = None

        if fix_available:
            remediation = (
                "Ruff provides an automatic fix for this finding. "
                "Review and apply the suggested fix."
            )

        metadata: dict[str, str] = {
            "engine": "ruff",
            "rule_code": code,
            "fix_available": str(fix_available).lower(),
        }

        if column >= 1:
            metadata["column"] = str(column)

        findings.append(
            AnalyzerFinding(
                severity=severity,
                category="quality",
                rule_id=code,
                title=code,
                description=message,
                file=file_path,
                line=max(1, line),
                confidence=1.0,
                remediation=remediation,
                metadata=metadata,
            )
        )

    return findings


def ruff_severity(rule_code: str) -> str:
    """
    Map Ruff rule families to Verion severity.

    Ruff itself does not provide a reliable security severity scale for
    every rule. Therefore Verion uses a conservative deterministic mapping.

    Security-oriented Ruff rules are treated as HIGH.
    Most correctness/style rules are MEDIUM or LOW.

    This function can later be replaced with a comprehensive rule-level
    policy table once the scoring methodology is finalized.
    """

    code = rule_code.upper().strip()

    # Ruff security rules commonly associated with the flake8-bandit
    # plugin use the S prefix.
    if code.startswith("S"):
        return "high"

    # Bugbear rules can indicate potentially dangerous Python behavior,
    # but not every B rule is security-critical.
    if code.startswith("B"):
        return "medium"

    # Pylint-style correctness rules.
    if code.startswith("PL"):
        return "medium"

    # Pyflakes / undefined-name / import problems.
    if code.startswith(("F", "E9")):
        return "medium"

    # Type-checking-related rules.
    if code.startswith("TC"):
        return "low"

    # Complexity rules.
    if code.startswith("C"):
        return "low"

    # Formatting/import-order/style rules.
    if code.startswith(("E", "W", "I", "UP", "SIM", "RET", "RUF")):
        return "low"

    # Unknown Ruff rule:
    # do not exaggerate its impact.
    return normalize_severity("medium")