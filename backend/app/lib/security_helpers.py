from datetime import UTC, datetime
from typing import Any

from app.lib.dashboard_helpers import format_datetime

SECURITY_CATEGORIES = ("security", "secret", "dependency")

SUPPORTED_SCANNERS = (
    "semgrep",
    "bandit",
    "ruff",
    "eslint",
    "detect-secrets",
    "pip-audit",
)


def build_security_posture(
    *,
    score: float | None,
    severity_counts: dict[str, int],
    has_analysis_data: bool,
) -> dict[str, str]:
    if not has_analysis_data or score is None:
        return {
            "label": "NOT ASSESSED",
            "level": "unavailable",
            "explanation": "Connect repositories and run analysis to establish a security posture baseline.",
        }

    critical = int(severity_counts.get("critical", 0))
    high = int(severity_counts.get("high", 0))
    medium = int(severity_counts.get("medium", 0))

    if critical > 0:
        return {
            "label": "CRITICAL EXPOSURE",
            "level": "critical",
            "explanation": (
                f"{critical} critical finding{'s' if critical != 1 else ''} require immediate review "
                "before release."
            ),
        }
    if high > 0 or score < 40:
        return {
            "label": "ELEVATED RISK",
            "level": "high",
            "explanation": (
                f"{high} high-severity finding{'s' if high != 1 else ''} detected. "
                "Prioritize remediation in affected repositories."
            ),
        }
    if medium > 0 or score < 70:
        return {
            "label": "MODERATE RISK",
            "level": "medium",
            "explanation": (
                f"Security score {score:.0f} with {medium} medium finding{'s' if medium != 1 else ''}. "
                "Schedule remediation for tracked issues."
            ),
        }
    return {
        "label": "STRONG POSTURE",
        "level": "healthy",
        "explanation": (
            f"Security score {score:.0f} with no critical or high findings in the latest analysis."
        ),
    }


def build_security_freshness(
    *,
    has_analysis_data: bool,
    analysis_running: bool,
    last_analyzed_at: Any,
    repositories_failed: int,
    repositories_stale: int,
) -> dict[str, Any]:
    if analysis_running:
        return {
            "status": "running",
            "label": "Analysis running",
            "is_stale": False,
            "last_analyzed_at": format_datetime(last_analyzed_at),
            "analysis_running": True,
        }
    if not has_analysis_data:
        return {
            "status": "unavailable",
            "label": "Not analyzed",
            "is_stale": False,
            "last_analyzed_at": None,
            "analysis_running": False,
        }
    if repositories_failed > 0:
        return {
            "status": "failed",
            "label": "Some repository analyses failed",
            "is_stale": True,
            "last_analyzed_at": format_datetime(last_analyzed_at),
            "analysis_running": False,
        }
    if repositories_stale > 0:
        return {
            "status": "stale",
            "label": "Some repositories have outdated analysis",
            "is_stale": True,
            "last_analyzed_at": format_datetime(last_analyzed_at),
            "analysis_running": False,
        }
    return {
        "status": "current",
        "label": "Analysis current",
        "is_stale": False,
        "last_analyzed_at": format_datetime(last_analyzed_at),
        "analysis_running": False,
    }


def is_repository_analysis_stale(last_analyzed_at: Any, *, stale_days: int = 7) -> bool:
    if last_analyzed_at is None:
        return True
    if not isinstance(last_analyzed_at, datetime):
        return False
    analyzed = last_analyzed_at if last_analyzed_at.tzinfo else last_analyzed_at.replace(tzinfo=UTC)
    age = datetime.now(UTC) - analyzed
    return age.days >= stale_days


def normalize_scanner_name(name: str) -> str:
    lowered = name.lower().replace("_", "-")
    mapping = {
        "dependencyanalyzer": "pip-audit",
        "secretsanalyzer": "detect-secrets",
        "semgrepanalyzer": "semgrep",
        "banditanalyzer": "bandit",
        "ruffanalyzer": "ruff",
        "eslintanalyzer": "eslint",
    }
    return mapping.get(lowered, lowered)
