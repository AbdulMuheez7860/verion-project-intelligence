from typing import Any

from app.lib.dashboard_helpers import format_datetime
from app.lib.security_helpers import build_security_freshness, is_repository_analysis_stale

SUPPORTED_SCANNERS = ("pip-audit",)

ECOSYSTEM_COVERAGE: list[dict[str, Any]] = [
    {
        "key": "python",
        "label": "Python (requirements.txt)",
        "supported": True,
        "note": "Scanned via pip-audit when requirements.txt is present.",
    },
    {
        "key": "npm",
        "label": "npm / package-lock",
        "supported": False,
        "note": "Not currently scanned.",
    },
    {
        "key": "maven",
        "label": "Maven / Gradle",
        "supported": False,
        "note": "Not currently scanned.",
    },
    {
        "key": "cargo",
        "label": "Cargo (Rust)",
        "supported": False,
        "note": "Not currently scanned.",
    },
    {
        "key": "go",
        "label": "Go modules",
        "supported": False,
        "note": "Not currently scanned.",
    },
]

UNAVAILABLE_DEPENDENCY_METRICS: list[dict[str, str]] = [
    {
        "key": "outdated_detection",
        "label": "Outdated dependency detection",
        "reason": "pip-audit reports vulnerabilities only. Version recency is not tracked in the current pipeline.",
    },
    {
        "key": "latest_version",
        "label": "Latest version comparison",
        "reason": "Latest package versions are not fetched from a registry. Displayed latest version mirrors the scanned version.",
    },
    {
        "key": "license_compliance",
        "label": "License compliance",
        "reason": "License data is not populated by the current pip-audit integration.",
    },
]


def build_dependency_posture(
    *,
    health_score: float | None,
    severity_counts: dict[str, int],
    vulnerable_count: int,
    has_analysis_data: bool,
) -> dict[str, str]:
    if not has_analysis_data or health_score is None:
        return {
            "label": "NOT ASSESSED",
            "level": "unavailable",
            "explanation": "Connect repositories and run analysis to establish dependency health.",
        }

    critical = int(severity_counts.get("critical", 0))
    high = int(severity_counts.get("high", 0))

    if critical > 0:
        return {
            "label": "CRITICAL EXPOSURE",
            "level": "critical",
            "explanation": (
                f"{critical} critical vulnerabilit{'ies' if critical != 1 else 'y'} in dependencies. "
                "Patch or upgrade affected packages before release."
            ),
        }
    if high > 0 or vulnerable_count >= 3:
        return {
            "label": "ELEVATED RISK",
            "level": "high",
            "explanation": (
                f"{vulnerable_count} vulnerable dependenc{'ies' if vulnerable_count != 1 else 'y'} detected "
                f"({high} high severity)."
            ),
        }
    if vulnerable_count > 0 or (health_score is not None and health_score < 80):
        return {
            "label": "MODERATE RISK",
            "level": "medium",
            "explanation": (
                f"{vulnerable_count} vulnerable dependenc{'ies' if vulnerable_count != 1 else 'y'} "
                f"with health score {health_score:.0f}."
            ),
        }
    return {
        "label": "HEALTHY",
        "level": "healthy",
        "explanation": (
            f"Dependency health score {health_score:.0f} with no known critical or high vulnerabilities."
        ),
    }


def build_dependency_freshness(
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


def build_dependency_recommendations(
    *,
    severity_counts: dict[str, int],
    top_packages: list[dict[str, Any]],
    repositories: list[dict[str, Any]],
    repositories_stale: int,
    analysis_running: bool,
    vulnerable_count: int,
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    critical = int(severity_counts.get("critical", 0))
    high = int(severity_counts.get("high", 0))

    if critical > 0:
        recommendations.append({
            "id": "critical-deps",
            "label": "Patch critical dependency vulnerabilities",
            "description": f"{critical} critical vulnerabilit{'ies' if critical != 1 else 'y'} require immediate attention.",
            "priority": "high",
        })
    elif high > 0:
        recommendations.append({
            "id": "high-deps",
            "label": "Review high-severity dependency vulnerabilities",
            "description": f"{high} high-severity vulnerabilit{'ies' if high != 1 else 'y'} detected.",
            "priority": "high",
        })
    elif vulnerable_count > 0:
        recommendations.append({
            "id": "vulnerable-deps",
            "label": "Review vulnerable dependencies",
            "description": f"{vulnerable_count} vulnerable dependenc{'ies' if vulnerable_count != 1 else 'y'} tracked.",
            "priority": "medium",
        })

    if top_packages:
        top = top_packages[0]
        recommendations.append({
            "id": "top-package",
            "label": f"Prioritize {top.get('package_name', 'package')}",
            "description": (
                f"Affects {top.get('repository_count', 0)} repositor"
                f"{'ies' if top.get('repository_count', 0) != 1 else 'y'} "
                f"with {top.get('vulnerable_count', 0)} vulnerable instance(s)."
            ),
            "priority": "medium",
        })

    affected = [repo for repo in repositories if int(repo.get("vulnerable_count", 0)) > 0]
    if affected:
        worst = max(affected, key=lambda r: int(r.get("vulnerable_count", 0)))
        recommendations.append({
            "id": "repo-focus",
            "label": f"Focus on {worst.get('name', 'repository')}",
            "description": (
                f"{worst.get('vulnerable_count', 0)} vulnerable dependenc"
                f"{'ies' if worst.get('vulnerable_count', 0) != 1 else 'y'} in this repository."
            ),
            "priority": "medium",
        })

    if repositories_stale > 0:
        recommendations.append({
            "id": "stale-analysis",
            "label": "Re-run stale dependency analyses",
            "description": f"Dependency analysis is stale for {repositories_stale} repositor"
            f"{'ies' if repositories_stale != 1 else 'y'}.",
            "priority": "medium",
        })

    if analysis_running:
        recommendations.append({
            "id": "analysis-running",
            "label": "Dependency analysis in progress",
            "description": "Results will update when the current analysis run completes.",
            "priority": "low",
        })

    return recommendations


def format_analyzed_at(value: Any) -> str | None:
    return format_datetime(value)
