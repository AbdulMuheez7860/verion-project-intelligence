import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerFinding, normalize_severity
from app.analyzers.normalize import first_int, relative_path, truncate


class EslintAnalyzer:
    name = "eslint"

    def supports(self, workspace: Path) -> bool:
        """
        ESLint is applicable when the repository contains JavaScript or
        TypeScript source files.

        Configuration is intentionally checked during execution rather
        than here, so an applicable repository can report a meaningful
        'skipped' or 'failed' state instead of silently returning [].
        """

        if not workspace.exists() or not workspace.is_dir():
            return False

        extensions = (
            "*.js",
            "*.jsx",
            "*.ts",
            "*.tsx",
            "*.mjs",
            "*.cjs",
        )

        return any(
            workspace.rglob(pattern)
            for pattern in extensions
        )

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Execute ESLint using a Verion-controlled, globally installed
        ESLint binary against the repository's own configuration.

        We intentionally do NOT use:

            npx --yes eslint

        because that can download an arbitrary/current ESLint version,
        making Verion's analysis slower and less deterministic.

        SECURITY: we also intentionally do NOT execute
        ``<workspace>/node_modules/.bin/eslint`` even when present.
        The analyzed repository is untrusted input, and a committed
        ``node_modules`` directory (or a malicious ``eslint`` package
        pinned in package.json) would let the repository supply the
        exact binary Verion executes on the analysis host. Running
        repo-supplied executables violates the "never execute arbitrary
        repository code" requirement even though ESLint itself is a
        "linter" - a malicious version is still attacker-controlled
        native code execution. Only a globally installed ESLint that is
        part of the Verion analysis environment is used. If it is not
        configured, this analyzer reports UNAVAILABLE rather than
        falling back to repository-controlled code.
        """

        executable = self._find_eslint_executable(workspace)

        if executable is None:
            raise RuntimeError(
                "ESLint executable was not found. "
                "Install ESLint in the repository or configure ESLint "
                "in the Verion analysis environment."
            )

        command = [
            executable,
            ".",
            "--format",
            "json",
            "--no-error-on-unmatched-pattern",
        ]

        try:
            result = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "ESLint analysis exceeded the 120 second timeout."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Failed to start ESLint: {exc}"
            ) from exc

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # ESLint uses exit code 1 when lint violations are present.
        # That is a successful scan, not a scanner failure.
        #
        # Exit code 0 -> scan completed with no errors/warnings
        # Exit code 1 -> scan completed and reported findings
        # Other codes -> execution/configuration failure
        if result.returncode not in (0, 1):
            error_details = stderr or stdout or "Unknown ESLint error."

            raise RuntimeError(
                f"ESLint failed with exit code {result.returncode}: "
                f"{truncate(error_details, 500)}"
            )

        # A clean ESLint run can legitimately produce empty output.
        if result.returncode == 0 and not stdout:
            return []

        if not stdout:
            raise RuntimeError(
                "ESLint reported findings/errors but produced no JSON output."
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "ESLint returned invalid JSON output."
            ) from exc

        if not isinstance(payload, list):
            raise RuntimeError(
                "ESLint returned an unexpected JSON structure. "
                "Expected a list of file results."
            )

        return parse_eslint_results(
            payload,
            str(workspace),
        )

    @staticmethod
    def _find_eslint_executable(
        workspace: Path,
    ) -> str | None:
        """
        Find the Verion-controlled ESLint executable.

        Deliberately does NOT look inside the analyzed workspace
        (e.g. ``node_modules/.bin/eslint``) - see the security note in
        ``run()``. Only a globally installed ESLint on the analysis
        host is used.
        """

        return shutil.which("eslint")


def parse_eslint_results(
    payload: list[dict[str, Any]],
    workspace_root: str,
) -> list[AnalyzerFinding]:
    """
    Convert ESLint's JSON output into Verion's normalized findings.
    """

    findings: list[AnalyzerFinding] = []

    for file_result in payload:
        if not isinstance(file_result, dict):
            continue

        raw_file_path = str(
            file_result.get("filePath")
            or ""
        )

        file_path = relative_path(
            raw_file_path,
            workspace_root,
        )

        messages = file_result.get("messages", [])

        if not isinstance(messages, list):
            continue

        for message in messages:
            if not isinstance(message, dict):
                continue

            rule_id = str(
                message.get("ruleId")
                or "eslint.unknown"
            ).strip()

            description = truncate(
                str(
                    message.get("message")
                    or rule_id
                ).strip()
            )

            severity_value = message.get(
                "severity",
                1,
            )

            severity = eslint_severity(
                severity_value,
                rule_id,
            )

            line = first_int(
                message.get("line")
            )

            column = extract_column(
                message.get("column")
            )

            end_line = extract_optional_int(
                message.get("endLine")
            )

            end_column = extract_optional_int(
                message.get("endColumn")
            )

            message_type = str(
                message.get("nodeType")
                or ""
            ).strip()

            fix_available = (
                isinstance(message.get("fix"), dict)
                or isinstance(message.get("suggestions"), list)
                and bool(message.get("suggestions"))
            )

            remediation = None

            if fix_available:
                remediation = (
                    "ESLint provides an automatic or suggested fix "
                    "for this finding. Review the fix before applying it."
                )

            metadata: dict[str, str] = {
                "engine": "eslint",
                "severity": str(severity_value),
                "fix_available": str(
                    fix_available
                ).lower(),
            }

            if column is not None:
                metadata["column"] = str(column)

            if end_line is not None:
                metadata["end_line"] = str(end_line)

            if end_column is not None:
                metadata["end_column"] = str(end_column)

            if message_type:
                metadata["node_type"] = message_type

            if message.get("fatal") is True:
                metadata["fatal"] = "true"

            findings.append(
                AnalyzerFinding(
                    severity=severity,
                    category=determine_category(
                        rule_id=rule_id,
                        message=description,
                    ),
                    rule_id=rule_id,
                    title=build_title(rule_id),
                    description=description,
                    file=file_path,
                    line=max(1, line),
                    confidence=1.0,
                    remediation=remediation,
                    metadata=metadata,
                )
            )

    return findings


def eslint_severity(
    severity_value: Any,
    rule_id: str,
) -> str:
    """
    Normalize ESLint severity.

    ESLint's native values are:

        0 = off
        1 = warning
        2 = error

    Important:
    ESLint 'error' does NOT automatically mean security HIGH.

    Severity here represents the impact of the lint rule in Verion,
    not simply ESLint's numeric severity.

    Security-oriented rules are promoted to HIGH.
    Normal lint errors become MEDIUM.
    Warnings become LOW.
    """

    try:
        numeric_severity = int(severity_value)
    except (TypeError, ValueError):
        numeric_severity = 1

    if numeric_severity <= 0:
        return "info"

    if is_security_rule(rule_id):
        return "high"

    if numeric_severity >= 2:
        return "medium"

    return "low"


def is_security_rule(
    rule_id: str,
) -> bool:
    """
    Identify common ESLint security-oriented rule namespaces.

    This intentionally stays conservative. A complete security mapping
    should eventually be maintained per ESLint plugin/rule.
    """

    normalized = rule_id.lower().strip()

    security_prefixes = (
        "security/",
        "eslint-plugin-security/",
        "no-eval",
        "no-implied-eval",
        "no-new-func",
    )

    return normalized.startswith(
        security_prefixes
    )


def determine_category(
    *,
    rule_id: str,
    message: str,
) -> str:
    """
    Determine the normalized Verion category for an ESLint finding.
    """

    normalized_rule = rule_id.lower().strip()
    normalized_message = message.lower()

    if is_security_rule(rule_id):
        return "security"

    security_keywords = (
        "security",
        "injection",
        "xss",
        "cross-site scripting",
        "unsafe",
        "eval",
        "credential",
        "secret",
        "password",
        "token",
    )

    combined = (
        f"{normalized_rule} {normalized_message}"
    )

    if any(
        keyword in combined
        for keyword in security_keywords
    ):
        return "security"

    return "quality"


def build_title(
    rule_id: str,
) -> str:
    """
    Keep the rule ID as the stable title.

    The rule ID is important because users need to be able to search
    documentation and configure the underlying ESLint rule.
    """

    return rule_id


def extract_column(
    value: Any,
) -> int | None:
    """
    Safely extract an ESLint column number.
    """

    if value is None:
        return None

    try:
        column = int(value)
    except (TypeError, ValueError):
        return None

    return max(1, column)


def extract_optional_int(
    value: Any,
) -> int | None:
    """
    Safely extract an optional integer.
    """

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None