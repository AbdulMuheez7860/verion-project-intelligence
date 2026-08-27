"""Centralized dashboard metric definitions."""

METRIC_DEFINITIONS: dict[str, str] = {
    "engineering_health": (
        "Composite health assessment derived from completed repository analyses, "
        "weighted across security and code quality scores."
    ),
    "repositories": "Repositories connected to this workspace.",
    "open_pull_requests": "Pull requests currently open across connected repositories.",
    "security_findings": (
        "Open security-related findings from completed analyses "
        "(security, secret, and dependency categories)."
    ),
    "critical_findings": (
        "Open findings classified as critical by the configured analyzers."
    ),
    "high_risk_prs": (
        "Open pull requests with a completed risk assessment at or above the high-risk threshold (50+)."
    ),
    "repositories_requiring_attention": (
        "Repositories with failed analysis, no completed analysis, or elevated risk signals."
    ),
    "repository_health": "Average repository health score from completed analyses.",
    "security": "Average security score from completed repository analyses.",
    "code_quality": "Average code quality score from completed repository analyses.",
    "dependencies": "Dependency health derived from vulnerable package findings.",
    "pull_request_risk": "Average risk score across pull requests with completed assessments.",
}

TRENDS_BASELINE_MESSAGE = (
    "Verion needs multiple completed analyses to establish engineering trends."
)
