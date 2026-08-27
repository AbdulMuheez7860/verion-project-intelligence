import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerFinding, normalize_confidence, normalize_severity
from app.analyzers.normalize import first_int, relative_path, truncate


class BanditAnalyzer:
    name = "bandit"

    def supports(self, workspace: Path) -> bool:
        """
        Bandit is applicable when the repository contains Python files.
        """
        return workspace.exists() and workspace.is_dir() and any(
            workspace.rglob("*.py")
        )

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Run Bandit recursively against the repository.

        Bandit's exit codes must not be treated as simple success/failure:

            0 -> scan completed with no security findings
            1 -> scan completed and findings were detected
            other -> execution/configuration failure

        The previous implementation treated empty stdout and malformed
        JSON as a clean scan. That could produce false "secure" results.
        """

        executable = shutil.which("bandit")

        if executable is None:
            raise RuntimeError(
                "Bandit executable was not found in PATH. "
                "Install Bandit or configure the analyzer environment."
            )

        try:
            result = subprocess.run(
                [
                    executable,
                    "-r",
                    str(workspace),
                    "-f",
                    "json",
                    "-q",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Bandit analysis exceeded the 120 second timeout."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Failed to start Bandit: {exc}"
            ) from exc

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Bandit normally returns:
        #
        # 0 -> no issues
        # 1 -> issues found
        #
        # Other codes indicate a scanner failure.
        if result.returncode not in (0, 1):
            error_details = stderr or stdout or "Unknown Bandit error."

            raise RuntimeError(
                f"Bandit failed with exit code {result.returncode}: "
                f"{truncate(error_details, 500)}"
            )

        # No findings is valid only when Bandit successfully completed.
        if result.returncode == 0 and not stdout:
            return []

        if not stdout:
            raise RuntimeError(
                "Bandit completed with a non-zero findings status but "
                "produced no JSON output."
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Bandit returned invalid JSON output."
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Bandit returned an unexpected JSON structure. "
                "Expected an object containing a 'results' field."
            )

        # Bandit can include error information in the JSON response.
        # Do not hide scanner-level errors.
        errors = payload.get("errors", [])

        if errors:
            error_messages: list[str] = []

            if isinstance(errors, list):
                for error in errors[:5]:
                    if isinstance(error, dict):
                        message = (
                            error.get("reason")
                            or error.get("message")
                            or str(error)
                        )
                    else:
                        message = str(error)

                    error_messages.append(str(message))
            else:
                error_messages.append(str(errors))

            raise RuntimeError(
                "Bandit reported scan errors: "
                + " | ".join(error_messages)[:1000]
            )

        return parse_bandit_results(
            payload,
            str(workspace),
        )


def parse_bandit_results(
    payload: dict[str, Any],
    workspace_root: str,
) -> list[AnalyzerFinding]:
    """
    Convert Bandit's native JSON output into Verion's normalized findings.
    """

    findings: list[AnalyzerFinding] = []

    results = payload.get("results", [])

    if results is None:
        return findings

    if not isinstance(results, list):
        raise ValueError(
            "Bandit 'results' field must be a list."
        )

    for item in results:
        if not isinstance(item, dict):
            continue

        test_id = str(
            item.get("test_id")
            or "bandit.unknown"
        ).strip()

        test_name = str(
            item.get("test_name")
            or test_id
        ).strip()

        issue_text = truncate(
            str(
                item.get("issue_text")
                or test_name
                or test_id
            ).strip()
        )

        # Bandit provides issue_severity separately from issue_confidence.
        # Both must be preserved independently.
        severity = normalize_severity(
            str(
                item.get("issue_severity")
                or "medium"
            )
        )

        confidence = extract_confidence(
            item.get("issue_confidence")
        )

        line = first_int(
            item.get("line_number")
        )

        file_path = relative_path(
            str(
                item.get("filename")
                or ""
            ),
            workspace_root,
        )

        # Bandit can provide CWE information as:
        #
        # {
        #     "id": 78,
        #     "link": "..."
        # }
        #
        # Preserve the useful identifiers without copying the entire
        # nested structure.
        cwe = item.get("issue_cwe")

        cwe_id: str | None = None
        cwe_link: str | None = None

        if isinstance(cwe, dict):
            raw_cwe_id = cwe.get("id")

            if raw_cwe_id is not None:
                cwe_id = str(raw_cwe_id)

            raw_cwe_link = cwe.get("link")

            if raw_cwe_link:
                cwe_link = str(raw_cwe_link)

        metadata: dict[str, str] = {
            "engine": "bandit",
            "test_id": test_id,
            "test_name": test_name,
        }

        if cwe_id:
            metadata["cwe"] = cwe_id

        if cwe_link:
            metadata["cwe_link"] = cwe_link

        # Bandit also provides line_range and code snippets.
        line_range = item.get("line_range")

        if isinstance(line_range, list) and line_range:
            metadata["line_range"] = ",".join(
                str(value)
                for value in line_range[:20]
            )

        code = item.get("code")

        if isinstance(code, str) and code.strip():
            metadata["code_snippet"] = truncate(
                code.strip(),
                500,
            )

        findings.append(
            AnalyzerFinding(
                severity=severity,
                category="security",
                rule_id=test_id,
                title=build_title(
                    test_id=test_id,
                    test_name=test_name,
                ),
                description=issue_text,
                file=file_path,
                line=max(1, line),
                confidence=confidence,
                remediation=build_remediation(
                    item=item,
                    cwe_id=cwe_id,
                ),
                metadata=metadata,
            )
        )

    return findings


def extract_confidence(
    value: Any,
) -> float | None:
    """
    Normalize Bandit's confidence values.

    Bandit normally returns:
        HIGH
        MEDIUM
        LOW

    but numeric values are also supported defensively.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return normalize_confidence(
            float(value)
        )

    normalized = str(value).strip().lower()

    mapping = {
        "high": 0.90,
        "medium": 0.70,
        "low": 0.40,
    }

    if normalized in mapping:
        return mapping[normalized]

    try:
        return normalize_confidence(
            float(normalized)
        )
    except (TypeError, ValueError):
        return None


def build_title(
    *,
    test_id: str,
    test_name: str,
) -> str:
    """
    Produce a useful human-readable Bandit finding title.
    """

    if test_name and test_name != test_id:
        return f"{test_name} ({test_id})"

    return test_id


def build_remediation(
    *,
    item: dict[str, Any],
    cwe_id: str | None,
) -> str | None:
    """
    Generate conservative remediation guidance.

    Bandit's JSON does not consistently contain a machine-readable fix,
    so Verion should not invent a specific patch.
    """

    issue_text = str(
        item.get("issue_text")
        or ""
    ).strip()

    if not issue_text:
        return None

    if cwe_id:
        return (
            f"Review and remediate the reported Bandit security issue "
            f"according to CWE-{cwe_id}. "
            f"Finding: {truncate(issue_text, 400)}"
        )

    return (
        "Review the reported Bandit security issue and apply the "
        f"appropriate secure implementation. "
        f"Finding: {truncate(issue_text, 400)}"
    )