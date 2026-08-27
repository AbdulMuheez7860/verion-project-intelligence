import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerFinding
from app.analyzers.normalize import (
    first_int,
    normalize_confidence,
    normalize_severity,
    relative_path,
    truncate,
)


class SecretDetectionAnalyzer:
    name = "detect-secrets"

    def supports(self, workspace: Path) -> bool:
        """
        Secret scanning applies to any valid repository directory.
        """
        return workspace.exists() and workspace.is_dir()

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Run detect-secrets against the repository.

        Important:
        - Scanner unavailable -> explicit failure.
        - Scanner timeout -> explicit failure.
        - Invalid JSON -> explicit failure.
        - Empty successful output -> failure, not zero findings.

        This prevents Verion from incorrectly reporting:
            "0 secrets found"

        when the scanner actually failed.
        """
        executable = shutil.which("detect-secrets")

        if executable is None:
            raise RuntimeError(
                "detect-secrets executable was not found in PATH. "
                "Install detect-secrets in the Verion analysis environment."
            )

        try:
            result = subprocess.run(
                [
                    executable,
                    "scan",
                    str(workspace),
                    "--all-files",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Secret detection exceeded the 180 second timeout."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Failed to start detect-secrets: {exc}"
            ) from exc

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if not stdout:
            if result.returncode == 0:
                raise RuntimeError(
                    "detect-secrets completed successfully but produced "
                    "no JSON output."
                )

            error_details = stderr or "Unknown detect-secrets error."

            raise RuntimeError(
                f"detect-secrets failed with exit code "
                f"{result.returncode}: "
                f"{truncate(error_details, 500)}"
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            error_details = stderr or "Invalid JSON returned by scanner."

            raise RuntimeError(
                "detect-secrets returned invalid JSON output. "
                f"{truncate(error_details, 500)}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "detect-secrets returned an unexpected JSON structure. "
                "Expected an object containing a 'results' field."
            )

        if "results" not in payload:
            raise RuntimeError(
                "detect-secrets JSON response does not contain "
                "the expected 'results' field."
            )

        # Non-zero exit codes must not silently become successful analysis.
        if result.returncode != 0:
            error_details = stderr or "Unknown detect-secrets error."

            raise RuntimeError(
                f"detect-secrets failed with exit code "
                f"{result.returncode}: "
                f"{truncate(error_details, 500)}"
            )

        return parse_detect_secrets_results(
            payload,
            str(workspace),
        )


def parse_detect_secrets_results(
    payload: dict[str, Any],
    workspace_root: str,
) -> list[AnalyzerFinding]:
    """
    Convert detect-secrets output into Verion findings.

    A detect-secrets match is a potential secret, not automatically
    proof that a credential is active.

    Therefore:
        verified   -> critical / very high confidence
        unverified -> high / high confidence
    """
    findings: list[AnalyzerFinding] = []

    results = payload.get("results", {})

    if results is None:
        return findings

    if not isinstance(results, dict):
        raise ValueError(
            "detect-secrets 'results' field must be an object."
        )

    for file_path, secrets in results.items():
        if not isinstance(secrets, list):
            continue

        relative = relative_path(
            str(file_path),
            workspace_root,
        )

        # Ignore malformed paths rather than creating broken findings.
        if not relative:
            continue

        for secret in secrets:
            if not isinstance(secret, dict):
                continue

            rule_id = str(
                secret.get("type") or "secret.unknown"
            ).strip()

            if not rule_id:
                rule_id = "secret.unknown"

            line = first_int(
                secret.get("line_number"),
                default=1,
            )

            confidence = determine_confidence(secret)
            severity = determine_severity(secret)

            metadata: dict[str, str] = {
                "engine": "detect-secrets",
                "detector": rule_id,
            }

            is_verified = secret.get("is_verified")

            if isinstance(is_verified, bool):
                metadata["is_verified"] = str(
                    is_verified
                ).lower()

            remediation = (
                "Verify whether the detected value is an active credential. "
                "If active, rotate it immediately, remove it from source "
                "control, and store it in a secure secret-management system. "
                "If it was committed to Git history, rotate the credential "
                "even after removing the current file."
            )

            findings.append(
                AnalyzerFinding(
                    severity=severity,
                    category="secret",
                    rule_id=rule_id,
                    title=f"Potential secret: {rule_id}",
                    description=truncate(
                        build_description(
                            rule_id,
                            secret,
                        )
                    ),
                    file=relative,
                    line=max(1, line),
                    confidence=confidence,
                    remediation=remediation,
                    metadata=metadata,
                )
            )

    return findings


def determine_confidence(
    secret: dict[str, Any],
) -> float:
    """
    Determine confidence for a detect-secrets finding.

    If detect-secrets explicitly verifies the finding, confidence is
    very high.

    Otherwise it remains a high-confidence potential match, but not
    a guaranteed active credential.
    """
    verified = secret.get("is_verified")

    if verified is True:
        return normalize_confidence(
            0.98,
            default=0.98,
        ) or 0.98

    if verified is False:
        return normalize_confidence(
            0.85,
            default=0.85,
        ) or 0.85

    return normalize_confidence(
        0.90,
        default=0.90,
    ) or 0.90


def determine_severity(
    secret: dict[str, Any],
) -> str:
    """
    Determine severity based on verification state.

    Verified secret:
        critical

    Unverified potential secret:
        high
    """
    if secret.get("is_verified") is True:
        return normalize_severity("critical")

    return normalize_severity("high")


def build_description(
    rule_id: str,
    secret: dict[str, Any],
) -> str:
    """
    Generate a useful description without exposing the detected value.
    """
    verified = secret.get("is_verified")

    if verified is True:
        return (
            f"detect-secrets identified a verified potential credential "
            f"using the {rule_id} detector."
        )

    return (
        f"detect-secrets identified a potential credential using the "
        f"{rule_id} detector. The match should be manually verified."
    )