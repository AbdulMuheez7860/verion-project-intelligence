import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerFinding, normalize_confidence, normalize_severity
from app.analyzers.normalize import first_int, relative_path, truncate


class SemgrepAnalyzer:
    name = "semgrep"

    def supports(self, workspace: Path) -> bool:
        """
        Semgrep can analyze most source repositories.

        The workspace itself must exist and be a directory.
        """
        return workspace.exists() and workspace.is_dir()

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Run Semgrep and normalize its JSON output.

        Semgrep's return codes must be handled carefully.

        Expected behavior:
            0 -> scan completed successfully
            1 -> findings were detected / scan completed with findings
            other -> Semgrep execution/configuration failure

        An empty stdout is therefore NOT automatically treated as a clean
        repository.
        """

        executable = shutil.which("semgrep")

        if executable is None:
            raise RuntimeError(
                "Semgrep executable was not found in PATH. "
                "Install Semgrep or configure the analyzer environment."
            )

        try:
            result = subprocess.run(
                [
                    executable,
                    "scan",
                    "--quiet",
                    "--json",
                    "--config",
                    "p/default",
                    str(workspace),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Semgrep analysis exceeded the 180 second timeout."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Failed to start Semgrep: {exc}"
            ) from exc

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Semgrep normally uses:
        #
        # 0 = successful scan with no findings
        # 1 = findings / scan completed with findings
        #
        # Other exit codes indicate an execution/configuration failure.
        if result.returncode not in (0, 1):
            error_details = stderr or stdout or "Unknown Semgrep error."

            raise RuntimeError(
                f"Semgrep failed with exit code {result.returncode}: "
                f"{truncate(error_details, 500)}"
            )

        # A successful Semgrep run can legitimately return no findings.
        if result.returncode == 0 and not stdout:
            return []

        if not stdout:
            raise RuntimeError(
                "Semgrep completed with findings/error status but "
                "produced no JSON output."
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Semgrep returned invalid JSON output."
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Semgrep returned an unexpected JSON structure. "
                "Expected an object containing a 'results' field."
            )

        # Semgrep may return errors inside the JSON response even when the
        # process itself exits successfully. These errors must not be hidden.
        scan_errors = payload.get("errors", [])

        if scan_errors:
            error_messages: list[str] = []

            if isinstance(scan_errors, list):
                for error in scan_errors[:5]:
                    if isinstance(error, dict):
                        message = (
                            error.get("message")
                            or error.get("error")
                            or str(error)
                        )
                    else:
                        message = str(error)

                    error_messages.append(str(message))

            else:
                error_messages.append(str(scan_errors))

            raise RuntimeError(
                "Semgrep reported scan errors: "
                + " | ".join(error_messages)[:1000]
            )

        return parse_semgrep_results(
            payload,
            str(workspace),
        )


def parse_semgrep_results(
    payload: dict[str, Any],
    workspace_root: str,
) -> list[AnalyzerFinding]:
    """
    Convert Semgrep's native JSON findings into Verion's normalized format.
    """

    findings: list[AnalyzerFinding] = []

    results = payload.get("results", [])

    if results is None:
        return findings

    if not isinstance(results, list):
        raise ValueError(
            "Semgrep 'results' field must be a list."
        )

    for item in results:
        if not isinstance(item, dict):
            continue

        check_id = str(
            item.get("check_id")
            or "semgrep.unknown"
        ).strip()

        extra = item.get("extra")

        if not isinstance(extra, dict):
            extra = {}

        # -------------------------------------------------------------
        # Severity
        # -------------------------------------------------------------
        raw_severity = extra.get("severity")

        severity = normalize_severity(
            str(raw_severity)
            if raw_severity
            else "medium"
        )

        # -------------------------------------------------------------
        # Category
        # -------------------------------------------------------------
        category = determine_category(
            check_id=check_id,
            extra=extra,
        )

        # -------------------------------------------------------------
        # File path
        # -------------------------------------------------------------
        raw_path = str(
            item.get("path")
            or ""
        )

        path = relative_path(
            raw_path,
            workspace_root,
        )

        # -------------------------------------------------------------
        # Source location
        # -------------------------------------------------------------
        start = item.get("start")

        line = 1
        column = 1

        if isinstance(start, dict):
            line = first_int(
                start.get("line")
            )

            raw_column = start.get("col")

            try:
                column = int(raw_column)
            except (TypeError, ValueError):
                column = 1

        # -------------------------------------------------------------
        # Message
        # -------------------------------------------------------------
        message = truncate(
            str(
                extra.get("message")
                or check_id
            ).strip()
        )

        # -------------------------------------------------------------
        # Confidence
        #
        # Semgrep's JSON may contain metadata such as:
        #
        #   confidence: HIGH
        #
        # or numeric values depending on the rule.
        # -------------------------------------------------------------
        confidence = extract_confidence(extra)

        # -------------------------------------------------------------
        # Remediation
        #
        # Semgrep may expose:
        #
        #   fix
        #   fix_regex
        #
        # Do not blindly stringify arbitrary dictionaries as remediation.
        # -------------------------------------------------------------
        remediation = extract_remediation(extra)

        # -------------------------------------------------------------
        # Metadata
        # -------------------------------------------------------------
        metadata: dict[str, str] = {
            "engine": "semgrep",
            "check_id": check_id,
        }

        if column >= 1:
            metadata["column"] = str(column)

        metadata.update(
            extract_metadata(extra)
        )

        findings.append(
            AnalyzerFinding(
                severity=severity,
                category=category,
                rule_id=check_id,
                title=build_title(check_id, extra),
                description=message,
                file=path,
                line=max(1, line),
                confidence=confidence,
                remediation=remediation,
                metadata=metadata,
            )
        )

    return findings


def determine_category(
    *,
    check_id: str,
    extra: dict[str, Any],
) -> str:
    """
    Determine Verion's normalized finding category.

    Semgrep rules can contain category information inside metadata.
    When unavailable, use conservative rule-ID/message heuristics.
    """

    metadata = extra.get("metadata")

    if isinstance(metadata, dict):
        category = metadata.get("category")

        if category:
            normalized = str(category).strip().lower()

            category_mapping = {
                "security": "security",
                "secrets": "secret",
                "secret": "secret",
                "correctness": "quality",
                "quality": "quality",
                "performance": "performance",
                "reliability": "quality",
                "maintainability": "quality",
            }

            if normalized in category_mapping:
                return category_mapping[normalized]

    combined = check_id.lower()

    message = str(
        extra.get("message") or ""
    ).lower()

    combined = f"{combined} {message}"

    secret_keywords = (
        "secret",
        "credential",
        "password",
        "api-key",
        "apikey",
        "private-key",
        "private_key",
        "token",
    )

    if any(keyword in combined for keyword in secret_keywords):
        return "secret"

    performance_keywords = (
        "performance",
        "slow",
        "inefficient",
        "complexity",
    )

    if any(keyword in combined for keyword in performance_keywords):
        return "performance"

    return "security"


def extract_confidence(
    extra: dict[str, Any],
) -> float | None:
    """
    Extract and normalize Semgrep confidence metadata.

    Supports values such as:

        0.95
        95
        HIGH
        MEDIUM
        LOW
    """

    value = extra.get("confidence")

    if value is None:
        metadata = extra.get("metadata")

        if isinstance(metadata, dict):
            value = metadata.get("confidence")

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return normalize_confidence(float(value))

    normalized = str(value).strip().lower()

    confidence_mapping = {
        "very high": 0.95,
        "very_high": 0.95,
        "high": 0.90,
        "medium": 0.70,
        "low": 0.40,
        "very low": 0.20,
        "very_low": 0.20,
    }

    if normalized in confidence_mapping:
        return confidence_mapping[normalized]

    try:
        return normalize_confidence(float(normalized))
    except (TypeError, ValueError):
        return None


def extract_remediation(
    extra: dict[str, Any],
) -> str | None:
    """
    Extract safe human-readable remediation information.
    """

    fix = extra.get("fix")

    if isinstance(fix, str) and fix.strip():
        return truncate(fix.strip(), 1000)

    fix_regex = extra.get("fix-regex")

    if isinstance(fix_regex, dict):
        replacement = fix_regex.get("replacement")

        if replacement:
            return (
                "Semgrep provides an automated regex-based fix. "
                f"Suggested replacement: {truncate(str(replacement), 500)}"
            )

    return None


def extract_metadata(
    extra: dict[str, Any],
) -> dict[str, str]:
    """
    Extract useful Semgrep metadata without copying large nested objects
    into MongoDB.
    """

    result: dict[str, str] = {}

    metadata = extra.get("metadata")

    if not isinstance(metadata, dict):
        return result

    useful_fields = (
        "technology",
        "subcategory",
        "likelihood",
        "impact",
        "cwe",
        "owasp",
        "confidence",
    )

    for key in useful_fields:
        value = metadata.get(key)

        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            result[key] = str(value)

        elif isinstance(value, list):
            result[key] = ", ".join(
                str(item)
                for item in value[:10]
            )

    return result


def build_title(
    check_id: str,
    extra: dict[str, Any],
) -> str:
    """
    Produce a human-readable title while retaining the Semgrep rule ID.
    """

    metadata = extra.get("metadata")

    if isinstance(metadata, dict):
        name = metadata.get("name")

        if name:
            return f"{str(name).strip()} ({check_id})"

    return check_id