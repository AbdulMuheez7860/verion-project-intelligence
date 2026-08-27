from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


# Dependency files that can materially affect application behavior.
DEPENDENCY_MANIFESTS = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "composer.json",
    "composer.lock",
    "Gemfile",
    "Gemfile.lock",
}


SECURITY_SEVERITY_POINTS = {
    "critical": 12,
    "high": 8,
    "medium": 5,
    "low": 2,
}


REPOSITORY_RISK_POINTS = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 2,
}


@dataclass(frozen=True)
class PRRiskFactor:
    label: str
    contribution: int
    explanation: str


@dataclass(frozen=True)
class PRRiskScore:
    value: int
    level: str
    factors: list[PRRiskFactor]
    engine: str = "Verion Risk Engine v1"


@dataclass(frozen=True)
class PRRiskSignals:
    security_findings: list[dict[str, Any]]
    files_changed: int
    additions: int
    deletions: int
    changed_files: list[str]
    coverage_percent: float | None = None
    dependency_vulnerabilities: int = 0
    repository_risk_level: str | None = None
    prior_pr_risk_average: float | None = None


def _normalize_path(path: str) -> str:
    """
    Normalize repository paths without resolving them against the
    local filesystem.

    GitHub paths are always POSIX-style, regardless of the OS running
    Verion.
    """
    value = str(path or "").strip().replace("\\", "/")

    while value.startswith("./"):
        value = value[2:]

    value = value.lstrip("/")

    parts: list[str] = []

    for part in value.split("/"):
        if not part or part == ".":
            continue

        # Do not allow path traversal to affect matching.
        if part == "..":
            if parts:
                parts.pop()
            continue

        parts.append(part)

    return "/".join(parts)


def _risk_level(value: int) -> str:
    """
    Convert a 0-100 risk score into a user-facing risk level.
    """
    if value >= 70:
        return "critical"

    if value >= 50:
        return "high"

    if value >= 30:
        return "medium"

    return "low"


def _cap(value: int, maximum: int) -> int:
    return min(max(value, 0), maximum)


def _safe_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _security_factor(
    findings: list[dict[str, Any]],
) -> PRRiskFactor:
    """
    Score security findings associated with the changed files.

    Maximum contribution: 30 points.
    """
    points = 0

    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        severity = str(
            finding.get("severity", "low")
        ).strip().lower()

        if severity not in SECURITY_SEVERITY_POINTS:
            severity = "low"

        counts[severity] += 1
        points += SECURITY_SEVERITY_POINTS[severity]

    contribution = _cap(points, 30)
    total = sum(counts.values())

    if total == 0:
        explanation = (
            "No security, secret, or dependency findings "
            "were detected in the changed files."
        )
    else:
        parts = [
            f"{count} {severity}"
            for severity, count in counts.items()
            if count
        ]

        explanation = (
            f"{total} finding(s) detected in changed files "
            f"({', '.join(parts)})."
        )

    return PRRiskFactor(
        label="Security findings",
        contribution=contribution,
        explanation=explanation,
    )


def _change_size_factor(
    files_changed: int,
    additions: int,
    deletions: int,
) -> PRRiskFactor:
    """
    Score the absolute size of the change.

    Maximum contribution: 20 points.
    """
    files_changed = _safe_non_negative_int(files_changed)
    additions = _safe_non_negative_int(additions)
    deletions = _safe_non_negative_int(deletions)

    total_lines = additions + deletions

    file_points = _cap(files_changed // 2, 10)
    line_points = _cap(total_lines // 100, 10)

    contribution = _cap(
        file_points + line_points,
        20,
    )

    explanation = (
        f"{files_changed} file(s) changed with "
        f"{total_lines:,} lines modified "
        f"({additions:,} additions, {deletions:,} deletions)."
    )

    return PRRiskFactor(
        label="Change size",
        contribution=contribution,
        explanation=explanation,
    )


def _complexity_factor(
    files_changed: int,
    additions: int,
    deletions: int,
) -> PRRiskFactor:
    """
    Estimate change complexity using average lines modified per file.

    Maximum contribution: 20 points.

    This is a heuristic, not a true cyclomatic-complexity measurement.
    """
    files_changed = _safe_non_negative_int(files_changed)
    additions = _safe_non_negative_int(additions)
    deletions = _safe_non_negative_int(deletions)

    total_lines = additions + deletions

    if files_changed <= 0:
        avg_lines = float(total_lines)
    else:
        avg_lines = total_lines / files_changed

    contribution = _cap(
        int(avg_lines / 20),
        20,
    )

    divisor = max(files_changed, 1)

    explanation = (
        f"Average {avg_lines:.0f} lines modified per file "
        f"across {divisor} file(s)."
    )

    return PRRiskFactor(
        label="Change complexity",
        contribution=contribution,
        explanation=explanation,
    )


def _coverage_factor(
    coverage_percent: float | None,
) -> PRRiskFactor | None:
    """
    Score test coverage only when a valid coverage value is available.

    Maximum contribution: 15 points.

    Coverage is deliberately NOT assumed to be zero when unavailable.
    Missing coverage data should not artificially increase PR risk.
    """
    if coverage_percent is None:
        return None

    try:
        coverage = float(coverage_percent)
    except (TypeError, ValueError):
        return None

    coverage = max(0.0, min(100.0, coverage))

    if coverage < 50:
        contribution = 15
    elif coverage < 70:
        contribution = 9
    elif coverage < 80:
        contribution = 5
    else:
        contribution = 0

    explanation = (
        f"Reported test coverage is {coverage:.0f}%. "
        "Lower coverage increases change risk."
    )

    return PRRiskFactor(
        label="Test coverage",
        contribution=contribution,
        explanation=explanation,
    )


def _is_dependency_manifest(path: str) -> bool:
    """
    Determine whether a changed path is a dependency manifest.

    Handles files inside subdirectories, for example:

        backend/requirements.txt
        frontend/package.json
        services/api/pyproject.toml
    """
    normalized = _normalize_path(path)

    if not normalized:
        return False

    filename = PurePosixPath(normalized).name

    return (
        filename in DEPENDENCY_MANIFESTS
        or normalized in DEPENDENCY_MANIFESTS
    )


def _dependency_factor(
    changed_files: list[str],
    vulnerability_count: int,
) -> PRRiskFactor:
    """
    Score dependency-related changes.

    Maximum contribution: 15 points.
    """
    normalized_changed_files = [
        _normalize_path(path)
        for path in changed_files
        if _normalize_path(path)
    ]

    manifest_hits = [
        path
        for path in normalized_changed_files
        if _is_dependency_manifest(path)
    ]

    vulnerability_count = _safe_non_negative_int(
        vulnerability_count
    )

    manifest_points = 7 if manifest_hits else 0

    vulnerability_points = _cap(
        vulnerability_count * 3,
        8,
    )

    contribution = _cap(
        manifest_points + vulnerability_points,
        15,
    )

    if manifest_hits and vulnerability_count:
        explanation = (
            f"Dependency manifest(s) changed "
            f"({', '.join(manifest_hits[:3])}) and "
            f"{vulnerability_count} dependency vulnerability "
            f"finding(s) are associated with this change."
        )

    elif manifest_hits:
        explanation = (
            f"Dependency manifest(s) changed: "
            f"{', '.join(manifest_hits[:3])}."
        )

    elif vulnerability_count:
        explanation = (
            f"{vulnerability_count} dependency vulnerability "
            f"finding(s) are associated with the change."
        )

    else:
        explanation = (
            "No dependency manifest changes or dependency "
            "vulnerabilities were detected."
        )

    return PRRiskFactor(
        label="Dependency changes",
        contribution=contribution,
        explanation=explanation,
    )


def _historical_factor(
    repository_risk_level: str | None,
    prior_pr_risk_average: float | None,
) -> PRRiskFactor:
    """
    Incorporate repository-level and historical PR risk.

    Maximum contribution: 10 points.
    """
    normalized_repo_risk = str(
        repository_risk_level or ""
    ).strip().lower()

    if normalized_repo_risk not in REPOSITORY_RISK_POINTS:
        normalized_repo_risk = "low"

    repo_points = REPOSITORY_RISK_POINTS[
        normalized_repo_risk
    ]

    prior_points = 0
    prior_average: float | None = None

    if prior_pr_risk_average is not None:
        try:
            prior_average = float(prior_pr_risk_average)
        except (TypeError, ValueError):
            prior_average = None

    if prior_average is not None:
        prior_average = max(
            0.0,
            min(100.0, prior_average),
        )

        prior_points = _cap(
            int(prior_average / 10),
            5,
        )

    contribution = _cap(
        repo_points + prior_points,
        10,
    )

    if prior_average is not None:
        explanation = (
            f"Repository baseline risk is "
            f"{normalized_repo_risk}; "
            f"recent PR average risk is "
            f"{prior_average:.0f}/100."
        )
    else:
        explanation = (
            f"Repository baseline risk is "
            f"{normalized_repo_risk}."
        )

    return PRRiskFactor(
        label="Historical risk",
        contribution=contribution,
        explanation=explanation,
    )


def compute_pr_risk_score(
    signals: PRRiskSignals,
) -> PRRiskScore:
    """
    Compute the final Verion PR risk score.

    Score range:

        0   -> lowest risk
        100 -> highest risk

    Maximum theoretical factor contributions:

        Security findings  : 30
        Change size        : 20
        Complexity         : 20
        Coverage           : 15
        Dependencies       : 15
        Historical risk    : 10

    The final score is capped at 100.
    """
    factors: list[PRRiskFactor] = [
        _security_factor(
            signals.security_findings
        ),
        _change_size_factor(
            signals.files_changed,
            signals.additions,
            signals.deletions,
        ),
        _complexity_factor(
            signals.files_changed,
            signals.additions,
            signals.deletions,
        ),
    ]

    coverage_factor = _coverage_factor(
        signals.coverage_percent
    )

    if coverage_factor is not None:
        factors.append(coverage_factor)

    factors.append(
        _dependency_factor(
            signals.changed_files,
            signals.dependency_vulnerabilities,
        )
    )

    factors.append(
        _historical_factor(
            signals.repository_risk_level,
            signals.prior_pr_risk_average,
        )
    )

    total = _cap(
        sum(
            factor.contribution
            for factor in factors
        ),
        100,
    )

    return PRRiskScore(
        value=total,
        level=_risk_level(total),
        factors=factors,
    )


def file_matches_changed_paths(
    finding_file: str,
    changed_files: list[str],
) -> bool:
    """
    Determine whether a finding belongs to a changed file.

    IMPORTANT:
    This function intentionally does NOT compare only basenames.

    Bad behavior:

        src/config.py
        tests/config.py

    These are different files and must NOT match.

    Matching rules:

    1. Exact normalized path match.
    2. One path may contain the other when GitHub/local paths
       have different repository prefixes.

    No basename-only fallback is used.
    """
    finding = _normalize_path(finding_file)

    if not finding:
        return False

    for changed_file in changed_files:
        changed = _normalize_path(changed_file)

        if not changed:
            continue

        # Exact repository-relative match.
        if finding == changed:
            return True

        # Handle cases where one side contains a repository/workspace
        # prefix that the other side does not.
        if finding.endswith(f"/{changed}"):
            return True

        if changed.endswith(f"/{finding}"):
            return True

    return False


def filter_findings_for_changed_files(
    findings: list[dict[str, Any]],
    changed_files: list[str],
) -> list[dict[str, Any]]:
    """
    Return only findings belonging to files modified by the PR.

    This is critical for PR risk analysis.

    A repository may contain hundreds of historical findings.
    A PR should not receive risk points simply because an unrelated
    file elsewhere in the repository has a vulnerability.
    """
    if not changed_files:
        return []

    normalized_changed_files = [
        _normalize_path(path)
        for path in changed_files
        if _normalize_path(path)
    ]

    if not normalized_changed_files:
        return []

    filtered: list[dict[str, Any]] = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        finding_file = str(
            finding.get("file", "")
        )

        if file_matches_changed_paths(
            finding_file,
            normalized_changed_files,
        ):
            filtered.append(finding)

    return filtered