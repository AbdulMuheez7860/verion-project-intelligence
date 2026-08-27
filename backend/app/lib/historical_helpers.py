from typing import Any, Literal

MetricDirection = Literal["improved", "worsened", "unchanged", "unavailable"]

# Score metrics: higher is better
HIGHER_IS_BETTER = frozenset({
    "health_score",
    "security_score",
    "quality_score",
    "dependency_score",
})

# Count metrics: lower is better
LOWER_IS_BETTER = frozenset({
    "finding_total",
    "finding_critical",
    "finding_high",
    "finding_medium",
    "finding_low",
    "security_total",
    "security_critical",
    "security_high",
    "quality_total",
    "quality_critical",
    "dependency_total",
    "dependency_critical",
    "dependency_vulnerable",
    "pr_risk_score",
    "pr_high_risk",
    "pr_critical_risk",
})

# Material change thresholds
SCORE_MATERIAL_DELTA = 5.0
COUNT_MATERIAL_DELTA = 1


def severity_breakdown_from_findings(
    findings: list[dict[str, Any]],
    *,
    categories: set[str],
) -> dict[str, int]:
    counts = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        if finding.get("category") not in categories:
            continue
        severity = str(finding.get("severity", "low"))
        counts["total"] += 1
        if severity in counts:
            counts[severity] += 1
    return counts


def breakdown_from_severity_counts(severity_counts: dict[str, int]) -> dict[str, int]:
    return {
        "total": sum(int(severity_counts.get(key, 0)) for key in ("critical", "high", "medium", "low")),
        "critical": int(severity_counts.get("critical", 0)),
        "high": int(severity_counts.get("high", 0)),
        "medium": int(severity_counts.get("medium", 0)),
        "low": int(severity_counts.get("low", 0)),
    }


def compare_metric(
    *,
    metric: str,
    current: float | int | None,
    previous: float | int | None,
    label: str | None = None,
) -> dict[str, Any]:
    if current is None and previous is None:
        return _unavailable_comparison(metric, label)

    if previous is None or current is None:
        return {
            "metric": metric,
            "label": label or metric,
            "current": current,
            "previous": previous,
            "delta": None,
            "percentage_change": None,
            "direction": "unavailable",
            "interpretation": "Insufficient history for comparison.",
            "available": False,
        }

    current_val = float(current)
    previous_val = float(previous)
    delta = round(current_val - previous_val, 2)
    direction = _direction_for_metric(metric, delta)
    percentage_change = _percentage_change(current_val, previous_val)

    return {
        "metric": metric,
        "label": label or metric,
        "current": current_val,
        "previous": previous_val,
        "delta": delta,
        "percentage_change": percentage_change,
        "direction": direction,
        "interpretation": _interpretation(metric, delta, direction),
        "available": True,
    }


def _direction_for_metric(metric: str, delta: float) -> MetricDirection:
    if delta == 0:
        return "unchanged"
    if metric in HIGHER_IS_BETTER:
        return "improved" if delta > 0 else "worsened"
    if metric in LOWER_IS_BETTER:
        return "improved" if delta < 0 else "worsened"
    return "unchanged"


def _percentage_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 1)


def _interpretation(metric: str, delta: float, direction: MetricDirection) -> str:
    if direction == "unchanged":
        return f"{metric.replace('_', ' ').title()} unchanged."
    if direction == "unavailable":
        return "Comparison unavailable."
    magnitude = abs(delta)
    if metric in HIGHER_IS_BETTER:
        return (
            f"Increased by {magnitude:.0f} points."
            if direction == "improved"
            else f"Decreased by {magnitude:.0f} points."
        )
    return (
        f"Reduced by {magnitude:.0f}."
        if direction == "improved"
        else f"Increased by {magnitude:.0f}."
    )


def _unavailable_comparison(metric: str, label: str | None) -> dict[str, Any]:
    return {
        "metric": metric,
        "label": label or metric,
        "current": None,
        "previous": None,
        "delta": None,
        "percentage_change": None,
        "direction": "unavailable",
        "interpretation": "Metric not available.",
        "available": False,
    }


def is_material_regression(metric: str, delta: float | None) -> bool:
    if delta is None:
        return False
    if metric in HIGHER_IS_BETTER:
        return delta <= -SCORE_MATERIAL_DELTA
    if metric in LOWER_IS_BETTER:
        return delta >= COUNT_MATERIAL_DELTA
    return False


def is_material_improvement(metric: str, delta: float | None) -> bool:
    if delta is None:
        return False
    if metric in HIGHER_IS_BETTER:
        return delta >= SCORE_MATERIAL_DELTA
    if metric in LOWER_IS_BETTER:
        return delta <= -COUNT_MATERIAL_DELTA
    return False


def overall_trend_direction(comparisons: list[dict[str, Any]]) -> str:
    available = [c for c in comparisons if c.get("available")]
    if not available:
        return "unavailable"
    improved = sum(1 for c in available if c.get("direction") == "improved")
    worsened = sum(1 for c in available if c.get("direction") == "worsened")
    if improved > worsened:
        return "improving"
    if worsened > improved:
        return "declining"
    return "stable"


def snapshot_trend_label(snapshot_count: int) -> str:
    if snapshot_count == 0:
        return "building"
    if snapshot_count == 1:
        return "established"
    return "trending"
