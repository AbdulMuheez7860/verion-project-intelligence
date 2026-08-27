from typing import Any

from app.schemas.dashboard import PRVerdict


def health_level_from_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"


def pr_verdict(risk_score: int | None) -> tuple[PRVerdict, str, str | None]:
    if risk_score is None:
        return (
            "analysis_unavailable",
            "Analysis unavailable",
            "Run repository analysis to score this pull request.",
        )
    if risk_score >= 70:
        return (
            "critical_risk",
            "Critical risk",
            "Risk score exceeds critical threshold. Resolve findings before merge.",
        )
    if risk_score >= 50:
        return (
            "high_risk",
            "High risk",
            "Multiple risk factors present. Review findings in changed files.",
        )
    if risk_score >= 30:
        return (
            "review_recommended",
            "Review recommended",
            "Moderate risk detected. Standard review recommended.",
        )
    return (
        "safe_to_merge",
        "Safe to merge",
        "No significant merge blockers detected by current analysis.",
    )


def pr_risk_level(risk_score: int | None) -> str | None:
    if risk_score is None:
        return None
    if risk_score >= 70:
        return "critical"
    if risk_score >= 50:
        return "high"
    if risk_score >= 30:
        return "medium"
    return "low"


def format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def duration_seconds(started_at: Any, completed_at: Any) -> int | None:
    if started_at is None or completed_at is None:
        return None
    if not hasattr(started_at, "timestamp") or not hasattr(completed_at, "timestamp"):
        return None
    delta = completed_at - started_at
    return max(0, int(delta.total_seconds()))
