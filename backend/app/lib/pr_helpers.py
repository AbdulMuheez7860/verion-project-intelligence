from typing import Any

from app.lib.dashboard_helpers import pr_verdict
from app.services.pr_risk_engine import DEPENDENCY_MANIFESTS

AREA_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("authentication", "Authentication", ("auth", "login", "session", "jwt", "oauth", "password")),
    ("api", "API", ("api/", "/routes/", "controller", "endpoint", "graphql")),
    ("database", "Database", ("db/", "migration", "models/", "schema", "sql")),
    ("infrastructure", "Infrastructure", ("docker", "k8s", "terraform", ".github/", "helm", "nginx")),
    ("dependencies", "Dependencies", tuple(DEPENDENCY_MANIFESTS)),
    ("frontend", "Frontend", (".tsx", ".jsx", ".vue", "frontend/", "src/components/")),
    ("backend", "Backend", (".py", "backend/", "app/", "services/")),
    ("configuration", "Configuration", (".env", "config", "settings", ".yaml", ".yml", ".toml")),
    ("tests", "Tests", ("test_", "tests/", "_test.", ".spec.")),
    ("documentation", "Documentation", ("docs/", "readme", ".md")),
]


def merge_safety_label(verdict_key: str) -> str:
    mapping = {
        "safe_to_merge": "LOW RISK",
        "review_recommended": "REVIEW RECOMMENDED",
        "high_risk": "HIGH RISK",
        "critical_risk": "BLOCKED",
        "analysis_unavailable": "ANALYSIS UNAVAILABLE",
    }
    return mapping.get(verdict_key, "ANALYSIS UNAVAILABLE")


def categorize_changed_file(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    filename = normalized.split("/")[-1]
    if filename in DEPENDENCY_MANIFESTS:
        return "dependencies"
    if any(token in normalized for token in ("auth", "login", "session", "jwt")):
        return "security"
    if filename.endswith((".yml", ".yaml", ".toml", ".env", ".ini", ".cfg")) or "config" in normalized:
        return "configuration"
    if "test" in normalized or filename.startswith("test_") or filename.endswith(("_test.py", ".spec.ts")):
        return "tests"
    if filename.endswith((".md", ".rst")) or normalized.startswith("docs/"):
        return "documentation"
    return "application"


def derive_affected_areas(
    changed_files: list[str],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    areas: dict[str, dict[str, Any]] = {}
    for area_key, label, tokens in AREA_RULES:
        file_hits = [
            path
            for path in changed_files
            if any(token in path.replace("\\", "/").lower() for token in tokens)
        ]
        finding_hits = [
            finding
            for finding in findings
            if any(
                token in str(finding.get("file", "")).replace("\\", "/").lower()
                for token in tokens
            )
        ]
        if file_hits or finding_hits:
            areas[area_key] = {
                "key": area_key,
                "label": label,
                "file_count": len(file_hits),
                "finding_count": len(finding_hits),
            }
    return list(areas.values())


def build_pr_freshness(
    *,
    risk_scored_at: Any,
    pr_updated_at: Any,
    repository_last_analyzed_at: Any,
    repository_analysis_status: str | None,
    risk_score: int | None,
) -> dict[str, Any]:
    from app.lib.dashboard_helpers import format_datetime

    scored_at = format_datetime(risk_scored_at)
    updated_at = format_datetime(pr_updated_at)
    repo_analyzed_at = format_datetime(repository_last_analyzed_at)

    is_stale = False
    if risk_score is None:
        return {
            "status": "analysis_unavailable",
            "label": "Analysis unavailable",
            "detail": "Run repository analysis to score this pull request.",
            "risk_scored_at": scored_at,
            "pr_updated_at": updated_at,
            "repository_last_analyzed_at": repo_analyzed_at,
            "is_stale": False,
        }

    if repository_analysis_status in {"queued", "running"}:
        return {
            "status": "analysis_running",
            "label": "Analysis running",
            "detail": "Repository analysis is in progress. PR risk may update when complete.",
            "risk_scored_at": scored_at,
            "pr_updated_at": updated_at,
            "repository_last_analyzed_at": repo_analyzed_at,
            "is_stale": True,
        }

    if scored_at and updated_at and pr_updated_at and risk_scored_at and pr_updated_at > risk_scored_at:
        is_stale = True
        return {
            "status": "pr_changed",
            "label": "PR changed after last analysis",
            "detail": "This pull request was updated after the last risk evaluation. Re-run analysis before merging.",
            "risk_scored_at": scored_at,
            "pr_updated_at": updated_at,
            "repository_last_analyzed_at": repo_analyzed_at,
            "is_stale": True,
        }

    if repository_analysis_status == "failed":
        return {
            "status": "repository_analysis_failed",
            "label": "Repository analysis failed",
            "detail": "Latest repository analysis failed. Risk may be based on outdated data.",
            "risk_scored_at": scored_at,
            "pr_updated_at": updated_at,
            "repository_last_analyzed_at": repo_analyzed_at,
            "is_stale": True,
        }

    if repository_analysis_status != "complete":
        return {
            "status": "repository_not_analyzed",
            "label": "Repository not fully analyzed",
            "detail": "Complete repository analysis to improve merge safety confidence.",
            "risk_scored_at": scored_at,
            "pr_updated_at": updated_at,
            "repository_last_analyzed_at": repo_analyzed_at,
            "is_stale": True,
        }

    return {
        "status": "current",
        "label": f"Analyzed {scored_at}" if scored_at else "Analysis complete",
        "detail": None,
        "risk_scored_at": scored_at,
        "pr_updated_at": updated_at,
        "repository_last_analyzed_at": repo_analyzed_at,
        "is_stale": is_stale,
    }


def build_pr_recommendations(
    *,
    verdict_key: str,
    freshness: dict[str, Any],
    security_findings: list[dict[str, Any]],
    quality_findings: list[dict[str, Any]],
    dependency_findings: list[dict[str, Any]],
    changed_files: list[dict[str, Any]],
    repository_analysis_status: str | None,
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []

    critical = [f for f in security_findings if f.get("severity") == "critical"]
    if critical:
        recommendations.append(
            {
                "id": "critical-security",
                "label": "Review critical security findings",
                "description": f"{len(critical)} critical security finding(s) affect changed files. Resolve before merge.",
                "priority": "high",
            },
        )

    if dependency_findings:
        manifests = [f for f in changed_files if f.get("category") == "dependencies"]
        if manifests:
            recommendations.append(
                {
                    "id": "dependency-review",
                    "label": "Review dependency changes",
                    "description": "Dependency manifests were modified. Verify package updates and vulnerabilities.",
                    "priority": "high",
                },
            )
        else:
            recommendations.append(
                {
                    "id": "dependency-findings",
                    "label": "Review dependency vulnerabilities",
                    "description": f"{len(dependency_findings)} dependency-related finding(s) in changed files.",
                    "priority": "medium",
                },
            )

    if freshness.get("is_stale"):
        recommendations.append(
            {
                "id": "stale-analysis",
                "label": "Re-run PR risk analysis",
                "description": freshness.get("detail") or "Analysis may be outdated for the current PR head.",
                "priority": "high",
            },
        )

    if repository_analysis_status != "complete":
        recommendations.append(
            {
                "id": "repo-analysis",
                "label": "Complete repository analysis",
                "description": "Repository analysis must complete to improve merge safety confidence.",
                "priority": "medium",
            },
        )

    high_risk_files = [f for f in changed_files if f.get("category") in {"security", "configuration"}]
    if high_risk_files and verdict_key in {"high_risk", "critical_risk"}:
        recommendations.append(
            {
                "id": "high-risk-files",
                "label": "Review high-risk file changes",
                "description": f"{len(high_risk_files)} changed file(s) are in security or configuration areas.",
                "priority": "medium",
            },
        )

    if quality_findings and verdict_key != "safe_to_merge":
        recommendations.append(
            {
                "id": "quality-review",
                "label": "Review code quality findings",
                "description": f"{len(quality_findings)} quality finding(s) in changed files.",
                "priority": "low",
            },
        )

    if verdict_key == "safe_to_merge" and not recommendations:
        recommendations.append(
            {
                "id": "standard-review",
                "label": "Perform standard code review",
                "description": "No significant merge blockers detected. Apply your team's normal review process.",
                "priority": "low",
            },
        )

    return recommendations


def verdict_fields(risk_score: int | None) -> tuple[str, str, str | None]:
    verdict_key, label, reason = pr_verdict(risk_score)
    return verdict_key, label, reason
