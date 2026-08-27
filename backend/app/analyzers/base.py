from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AnalyzerFinding:
    """
    A normalized finding produced by any repository analyzer.

    Analyzer implementations should convert their native output into
    this common structure before returning findings.
    """

    severity: str
    category: str
    rule_id: str
    title: str
    description: str
    file: str
    line: int

    # Confidence in the finding itself, expressed as 0.0 - 1.0.
    confidence: float | None = None

    # Human-readable remediation guidance.
    remediation: str | None = None

    # Additional analyzer-specific information.
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate the normalized finding at creation time.

        Invalid findings should fail immediately instead of contaminating
        the analysis results and scores.
        """

        valid_severities = {
            "critical",
            "high",
            "medium",
            "low",
            "info",
        }

        if self.severity not in valid_severities:
            raise ValueError(
                f"Invalid finding severity: {self.severity!r}. "
                f"Expected one of: {sorted(valid_severities)}"
            )

        if not self.category.strip():
            raise ValueError("Finding category cannot be empty.")

        if not self.rule_id.strip():
            raise ValueError("Finding rule_id cannot be empty.")

        if not self.title.strip():
            raise ValueError("Finding title cannot be empty.")

        if not self.description.strip():
            raise ValueError("Finding description cannot be empty.")

        if not self.file.strip():
            raise ValueError("Finding file cannot be empty.")

        if self.line < 1:
            raise ValueError(
                f"Finding line must be >= 1, got {self.line}."
            )

        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Finding confidence must be between 0.0 and 1.0, "
                f"got {self.confidence}."
            )


@dataclass(frozen=True)
class AnalyzerResult:
    """
    Result of executing an analyzer.

    This is deliberately different from AnalyzerFinding.

    An analyzer returning zero findings is a SUCCESSFUL analysis.

    An analyzer that crashes, times out, or cannot execute is a FAILED
    analysis and must never be represented as an empty finding list.
    """

    analyzer: str
    status: str

    findings: tuple[AnalyzerFinding, ...] = field(default_factory=tuple)

    duration_ms: int = 0

    error_code: str | None = None
    error_message: str | None = None

    skipped_reason: str | None = None

    version: str | None = None

    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        valid_statuses = {
            "completed",
            "failed",
            "skipped",
            "timeout",
        }

        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid analyzer status: {self.status!r}. "
                f"Expected one of: {sorted(valid_statuses)}"
            )

        if not self.analyzer.strip():
            raise ValueError("Analyzer name cannot be empty.")

        if self.duration_ms < 0:
            raise ValueError(
                f"Analyzer duration cannot be negative, got {self.duration_ms}."
            )

        if self.status == "completed":
            if self.error_code is not None or self.error_message is not None:
                raise ValueError(
                    "A completed analyzer cannot contain an error."
                )

        if self.status in {"failed", "timeout"}:
            if not self.error_code:
                raise ValueError(
                    f"{self.status.capitalize()} analyzer result "
                    "must contain error_code."
                )

        if self.status == "skipped" and not self.skipped_reason:
            raise ValueError(
                "A skipped analyzer result must contain skipped_reason."
            )

    @property
    def finding_count(self) -> int:
        """Number of normalized findings produced by this analyzer."""
        return len(self.findings)

    @property
    def succeeded(self) -> bool:
        """True only when the analyzer actually completed."""
        return self.status == "completed"

    @property
    def failed(self) -> bool:
        """True when analyzer execution failed or timed out."""
        return self.status in {"failed", "timeout"}

    @property
    def skipped(self) -> bool:
        """True when analyzer was intentionally not executed."""
        return self.status == "skipped"


class Analyzer(Protocol):
    """
    Contract implemented by every repository analyzer.

    Existing analyzers can continue implementing:
        supports(workspace)
        run(workspace)

    The orchestrator is responsible for converting exceptions and
    execution failures into AnalyzerResult objects.
    """

    name: str

    def supports(self, workspace: Path) -> bool:
        """
        Return True when this analyzer is applicable to the repository.
        """
        ...

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        """
        Execute the analyzer.

        IMPORTANT:
        - Return [] when analysis completed successfully and no findings exist.
        - Raise an exception when execution itself fails.
        - Do not silently convert execution errors into [].
        """
        ...


def normalize_confidence(value: float | int | None) -> float | None:
    """
    Normalize analyzer confidence values to the range 0.0 - 1.0.

    Supported inputs:
        None       -> None
        0.85       -> 0.85
        85         -> 0.85

    Values outside the valid range raise ValueError.
    """

    if value is None:
        return None

    numeric_value = float(value)

    if 0.0 <= numeric_value <= 1.0:
        return numeric_value

    if 1.0 < numeric_value <= 100.0:
        return numeric_value / 100.0

    raise ValueError(
        f"Confidence must be between 0 and 1, or between 0 and 100. "
        f"Got {value!r}."
    )


def normalize_severity(value: str | None) -> str:
    """
    Convert analyzer-specific severity names into Verion's standard
    severity vocabulary.

    Standard Verion severities:
        critical
        high
        medium
        low
        info
    """

    if not value:
        return "info"

    normalized = value.strip().lower()

    mapping = {
        "critical": "critical",
        "crit": "critical",

        "high": "high",
        "error": "high",
        "err": "high",

        "medium": "medium",
        "moderate": "medium",
        "warning": "medium",
        "warn": "medium",

        "low": "low",
        "minor": "low",

        "info": "info",
        "informational": "info",
        "notice": "info",
    }

    return mapping.get(normalized, "info")