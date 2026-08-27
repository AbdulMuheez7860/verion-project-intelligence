from typing import Any

from app.lib.dashboard_helpers import format_datetime
from app.lib.security_helpers import build_security_freshness, is_repository_analysis_stale, normalize_scanner_name

QUALITY_CATEGORIES = ("quality",)

SUPPORTED_QUALITY_SCANNERS = ("ruff", "eslint")

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

UNAVAILABLE_QUALITY_METRICS: list[dict[str, str]] = [
    {
        "key": "complexity",
        "label": "Average complexity",
        "reason": "Not measured. Requires cyclomatic complexity analysis beyond current Ruff/ESLint rules.",
    },
    {
        "key": "duplication",
        "label": "Duplication",
        "reason": "Not measured. Requires a duplication detector (e.g. jscpd, PMD CPD) integrated into the pipeline.",
    },
    {
        "key": "technical_debt",
        "label": "Technical debt",
        "reason": "Not estimated. No debt-hours model is configured for current quality findings.",
    },
    {
        "key": "coverage",
        "label": "Test coverage",
        "reason": "Not measured. Coverage tooling is not integrated into repository analysis.",
    },
]


def highest_severity(severities: list[str]) -> str | None:
    if not severities:
        return None
    return min(severities, key=lambda s: SEVERITY_RANK.get(s, 99))


def build_quality_posture(
    *,
    score: float | None,
    severity_counts: dict[str, int],
    has_analysis_data: bool,
) -> dict[str, str]:
    if not has_analysis_data or score is None:
        return {
            "label": "NOT ASSESSED",
            "level": "unavailable",
            "explanation": "Connect repositories and run analysis to establish a code quality baseline.",
        }

    critical = int(severity_counts.get("critical", 0))
    high = int(severity_counts.get("high", 0))
    medium = int(severity_counts.get("medium", 0))

    if critical > 0:
        return {
            "label": "CRITICAL ISSUES",
            "level": "critical",
            "explanation": (
                f"{critical} critical quality finding{'s' if critical != 1 else ''} detected. "
                "Address before merging further changes."
            ),
        }
    if high > 0 or score < 40:
        return {
            "label": "ELEVATED DEBT",
            "level": "high",
            "explanation": (
                f"{high} high-severity quality finding{'s' if high != 1 else ''}. "
                "Prioritize remediation in affected repositories."
            ),
        }
    if medium > 0 or score < 70:
        return {
            "label": "MODERATE CONCERNS",
            "level": "medium",
            "explanation": (
                f"Quality score {score:.0f} with {medium} medium finding{'s' if medium != 1 else ''}. "
                "Schedule cleanup in upcoming sprints."
            ),
        }
    return {
        "label": "STRONG QUALITY",
        "level": "healthy",
        "explanation": (
            f"Quality score {score:.0f} with no critical or high findings in the latest analysis."
        ),
    }


def build_quality_freshness(
    *,
    has_analysis_data: bool,
    analysis_running: bool,
    last_analyzed_at: Any,
    repositories_failed: int,
    repositories_stale: int,
) -> dict[str, Any]:
    return build_security_freshness(
        has_analysis_data=has_analysis_data,
        analysis_running=analysis_running,
        last_analyzed_at=last_analyzed_at,
        repositories_failed=repositories_failed,
        repositories_stale=repositories_stale,
    )


def filter_quality_scanners(executed: set[str]) -> set[str]:
    quality_scanners: set[str] = set()
    for name in executed:
        normalized = normalize_scanner_name(name)
        if normalized in SUPPORTED_QUALITY_SCANNERS:
            quality_scanners.add(normalized)
    return quality_scanners


def build_quality_recommendations(
    *,
    severity_counts: dict[str, int],
    top_rules: list[dict[str, Any]],
    repositories: list[dict[str, Any]],
    repositories_stale: int,
    analysis_running: bool,
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []

    critical = int(severity_counts.get("critical", 0))
    high = int(severity_counts.get("high", 0))
    if critical > 0:
        recommendations.append({
            "id": "critical-quality",
            "label": "Review critical quality findings",
            "description": f"{critical} critical quality finding{'s' if critical != 1 else ''} require review.",
            "priority": "high",
        })
    elif high > 0:
        recommendations.append({
            "id": "high-quality",
            "label": "Address high-severity quality issues",
            "description": f"{high} high-severity quality finding{'s' if high != 1 else ''} detected.",
            "priority": "high",
        })

    if top_rules:
        top = top_rules[0]
        rule_id = str(top.get("rule_id", "unknown"))
        count = int(top.get("count", 0))
        analyzer = top.get("analyzer") or "analyzer"
        recommendations.append({
            "id": "top-rule",
            "label": f"Investigate rule {rule_id}",
            "description": f"{count} finding(s) from {analyzer} — the most frequent quality issue pattern.",
            "priority": "medium",
        })

    affected = [repo for repo in repositories if int(repo.get("finding_count", 0)) > 0]
    if affected:
        worst = max(affected, key=lambda r: int(r.get("finding_count", 0)))
        if int(worst.get("finding_count", 0)) > 0:
            recommendations.append({
                "id": "repo-focus",
                "label": f"Focus on {worst.get('name', 'repository')}",
                "description": (
                    f"Highest concentration of quality findings "
                    f"({worst.get('finding_count', 0)} total)."
                ),
                "priority": "medium",
            })

    if repositories_stale > 0:
        recommendations.append({
            "id": "stale-analysis",
            "label": "Re-run stale repository analyses",
            "description": f"{repositories_stale} repositor{'ies' if repositories_stale != 1 else 'y'} "
            "have outdated quality analysis.",
            "priority": "medium",
        })

    if analysis_running:
        recommendations.append({
            "id": "analysis-running",
            "label": "Analysis in progress",
            "description": "Quality intelligence will update when the current analysis run completes.",
            "priority": "low",
        })

    return recommendations
