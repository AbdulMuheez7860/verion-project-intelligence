from dataclasses import dataclass
from typing import Any

from app.analyzers.normalize import SEVERITY_ORDER, SEVERITY_WEIGHTS


@dataclass(frozen=True)
class RiskMetrics:
    security_score: float
    code_quality_score: float
    health_score: float
    risk_level: str
    severity_counts: dict[str, int]


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        severity = str(finding.get("severity", "low"))
        if severity in counts:
            counts[severity] += 1
    return counts


def _score_from_penalties(counts: dict[str, int], *, cap: int = 100) -> float:
    penalty = sum(SEVERITY_WEIGHTS[severity] * count for severity, count in counts.items())
    return max(0.0, min(100.0, float(cap - penalty)))


def _risk_level(counts: dict[str, int]) -> str:
    if counts.get("critical", 0) > 0:
        return "critical"
    if counts.get("high", 0) > 0:
        return "high"
    if counts.get("medium", 0) > 0:
        return "medium"
    return "low"


def compute_risk_metrics(findings: list[dict[str, Any]]) -> RiskMetrics:
    security_categories = {"security", "secret", "dependency"}
    quality_categories = {"quality"}

    security_findings = [f for f in findings if f.get("category") in security_categories]
    quality_findings = [f for f in findings if f.get("category") in quality_categories]

    security_counts = _severity_counts(security_findings)
    quality_counts = _severity_counts(quality_findings)
    all_counts = _severity_counts(findings)

    security_score = _score_from_penalties(security_counts)
    code_quality_score = _score_from_penalties(quality_counts)
    health_score = round((security_score * 0.6) + (code_quality_score * 0.4), 1)

    return RiskMetrics(
        security_score=round(security_score, 1),
        code_quality_score=round(code_quality_score, 1),
        health_score=health_score,
        risk_level=_risk_level(all_counts),
        severity_counts=all_counts,
    )
