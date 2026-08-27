"""Professional report generation (spec sections 14-16).

Builds a report entirely from Verion's own stored data — repository record,
findings, dependencies, latest analysis run's analyzer_summary, and (where
available) the previous analysis snapshot for a trend comparison. Nothing in
the report is invented: sections for which no data exists say so explicitly
rather than being silently omitted or filled with a placeholder.

Authorization / IDOR note (spec section 16): reports are not stored as
separate objects with guessable ids. They are generated on demand, scoped
to `(repository_id, organization_id)`, where `organization_id` always comes
from the caller's authenticated membership context — never from client
input. Because there is no separate "report id" to guess, cross-organization
report access is structurally not possible via this endpoint: a request for
another org's repository_id simply 404s (RepositoryRepository.get_by_id
already filters by organization_id).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.repositories import RepositoryRepository
from app.services.repository_intelligence import RepositoryIntelligenceService

SEVERITY_ORDER = ["critical", "high", "medium", "low"]
SEVERITY_COLORS = {
    "critical": colors.HexColor("#b91c1c"),
    "high": colors.HexColor("#c2410c"),
    "medium": colors.HexColor("#a16207"),
    "low": colors.HexColor("#4d7c0f"),
}
MAX_FINDINGS_PER_CATEGORY = 50


class ReportGenerationService:
    def __init__(
        self,
        repositories: RepositoryRepository,
        findings: FindingRepository,
        dependencies: DependencyRepository,
        analysis_runs: AnalysisRunRepository,
        snapshots: AnalysisSnapshotRepository,
        intelligence: RepositoryIntelligenceService,
    ) -> None:
        self._repositories = repositories
        self._findings = findings
        self._dependencies = dependencies
        self._analysis_runs = analysis_runs
        self._snapshots = snapshots
        self._intelligence = intelligence

    # ------------------------------------------------------------------
    # Data assembly — shared by both PDF and JSON export so they never
    # diverge in content.
    # ------------------------------------------------------------------

    async def build_report_data(self, repository_id: str, organization_id: str) -> dict[str, Any] | None:
        repo_doc = await self._repositories.get_by_id(repository_id, organization_id)
        if not repo_doc:
            return None
        if repo_doc.get("analysis_status") != "complete":
            raise ValueError("This repository has no completed analysis. Run an analysis before generating a report.")

        intelligence = await self._intelligence.get_intelligence(repository_id, organization_id)
        latest_run = await self._analysis_runs.latest_for_repository(repository_id, organization_id)
        analyzer_summary = (latest_run.get("analyzer_summary") if latest_run else None) or {}

        all_findings = await self._findings.list_by_repository(repository_id, organization_id)
        findings_by_category: dict[str, list[dict[str, Any]]] = {}
        for f in all_findings:
            category = str(f.get("category") or "other")
            findings_by_category.setdefault(category, []).append(f)
        for category, items in findings_by_category.items():
            items.sort(key=lambda f: SEVERITY_ORDER.index(f.get("severity")) if f.get("severity") in SEVERITY_ORDER else 99)

        deps, dep_total = await self._dependencies.list_by_repository_paginated(
            repository_id, organization_id, skip=0, limit=500,
        )
        vulnerable_deps = [d for d in deps if d.get("status") in ("vulnerable", "critical")]

        trend = await self._build_trend(repository_id, organization_id, latest_run)

        analyzer_rows = []
        if isinstance(analyzer_summary, dict):
            for analyzer_name, info in analyzer_summary.items():
                if isinstance(info, dict):
                    analyzer_rows.append(
                        {
                            "analyzer": analyzer_name,
                            "status": info.get("status", "unknown"),
                            "finding_count": info.get("finding_count"),
                            "duration_seconds": info.get("duration_seconds"),
                            "error": info.get("error"),
                        },
                    )
                else:
                    analyzer_rows.append({"analyzer": analyzer_name, "status": str(info)})

        executed = [a for a in analyzer_rows if a["status"] not in ("not_applicable", "unavailable")]
        completed = [a for a in analyzer_rows if a["status"] == "completed"]
        coverage_pct = round((len(completed) / len(executed)) * 100, 1) if executed else None

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "repository": {
                "id": repository_id,
                "name": repo_doc.get("name"),
                "owner": repo_doc.get("owner"),
                "default_branch": repo_doc.get("default_branch"),
                "primary_language": repo_doc.get("language"),
                "html_url": repo_doc.get("html_url"),
            },
            "commit": {
                "sha": latest_run.get("commit_sha") if latest_run else None,
                "branch": latest_run.get("branch") if latest_run else None,
                "analyzed_at": str(latest_run.get("completed_at")) if latest_run and latest_run.get("completed_at") else None,
            },
            "scores": {
                "health": repo_doc.get("health_score"),
                "security": repo_doc.get("security_score"),
                "code_quality": repo_doc.get("code_quality_score"),
                "dependency": repo_doc.get("dependency_score"),
                "risk_level": repo_doc.get("risk_level"),
            },
            "analyzer_coverage": {
                "rows": analyzer_rows,
                "executed_count": len(executed),
                "completed_count": len(completed),
                "coverage_percent": coverage_pct,
            },
            "findings": {
                "total": len(all_findings),
                "by_category": {
                    category: {
                        "count": len(items),
                        "severity_counts": _severity_counts(items),
                        "items": [_finding_row(f) for f in items[:MAX_FINDINGS_PER_CATEGORY]],
                        "truncated": max(0, len(items) - MAX_FINDINGS_PER_CATEGORY),
                    }
                    for category, items in findings_by_category.items()
                },
            },
            "dependencies": {
                "total": dep_total,
                "vulnerable_count": len(vulnerable_deps),
                "vulnerable_items": [
                    {
                        "package": d.get("package_name"),
                        "current_version": d.get("current_version"),
                        "latest_version": d.get("latest_version"),
                        "severity": d.get("severity"),
                        "vulnerability": d.get("vulnerability"),
                        "ecosystem": d.get("ecosystem"),
                    }
                    for d in vulnerable_deps[:MAX_FINDINGS_PER_CATEGORY]
                ],
            },
            "trend": trend,
            "recommended_actions": [
                {"label": a.label, "description": a.description, "priority": a.priority}
                for a in (intelligence.recommended_actions if intelligence else [])
            ],
            "limitations": [
                "Static analysis cannot detect all defects; absence of findings is not proof of "
                "absence of issues.",
                "Analyzer coverage is partial — see the Analyzer Coverage section for which "
                "analyzers ran, and which were skipped or unavailable in this environment.",
                "Severity and confidence reflect the originating scanner's heuristics and may "
                "include false positives; each finding should be reviewed before action.",
                "This report reflects a single point-in-time analysis of the commit shown above.",
            ],
        }

    async def _build_trend(
        self,
        repository_id: str,
        organization_id: str,
        latest_run: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not latest_run:
            return {"available": False, "reason": "No analysis run found."}
        latest_snapshot = await self._snapshots.get_by_analysis_run(latest_run["id"], organization_id)
        if not latest_snapshot:
            return {"available": False, "reason": "No snapshot recorded for the latest analysis run."}
        captured_at = latest_snapshot.get("captured_at")
        if not captured_at:
            return {"available": False, "reason": "Latest snapshot has no timestamp."}
        previous = await self._snapshots.get_previous_snapshot(
            organization_id, repository_id=repository_id, before_captured_at=captured_at,
        )
        if not previous:
            return {"available": False, "reason": "No prior analysis snapshot to compare against — this is the first recorded analysis."}

        def _delta(key: str) -> float | None:
            cur = latest_snapshot.get(key)
            prev = previous.get(key)
            if cur is None or prev is None:
                return None
            return round(cur - prev, 2)

        return {
            "available": True,
            "compared_to_captured_at": str(previous.get("captured_at")),
            "health_score_delta": _delta("health_score"),
            "security_score_delta": _delta("security_score"),
            "quality_score_delta": _delta("quality_score"),
            "dependency_score_delta": _delta("dependency_score"),
            "finding_count_delta": (
                (latest_snapshot.get("finding_counts") or {}).get("total", 0)
                - (previous.get("finding_counts") or {}).get("total", 0)
                if latest_snapshot.get("finding_counts") and previous.get("finding_counts")
                else None
            ),
            "note": (
                "This compares aggregate scores and counts between the two most recent analysis "
                "snapshots. It is not a per-finding new/resolved/regressed diff — Verion does not "
                "yet track individual finding identity across runs."
            ),
        }

    # ------------------------------------------------------------------
    # PDF rendering
    # ------------------------------------------------------------------

    def render_pdf(self, data: dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("VerionTitle", parent=styles["Title"], fontSize=20, spaceAfter=4)
        h2 = ParagraphStyle("VerionH2", parent=styles["Heading2"], spaceBefore=16, spaceAfter=6)
        body = styles["BodyText"]
        muted = ParagraphStyle("Muted", parent=styles["BodyText"], textColor=colors.grey, fontSize=9)

        story: list[Any] = []
        repo = data["repository"]
        story.append(Paragraph(f"Verion Analysis Report — {repo.get('name', 'Repository')}", title_style))
        story.append(
            Paragraph(
                f"Generated {data['generated_at']} · Commit {data['commit'].get('sha') or 'unknown'} on "
                f"{data['commit'].get('branch') or 'unknown branch'}",
                muted,
            ),
        )
        story.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), spaceBefore=8, spaceAfter=8))

        # Executive summary
        story.append(Paragraph("Executive Summary", h2))
        scores = data["scores"]
        score_table_data = [["Metric", "Score"]]
        for label, key in [
            ("Overall Health", "health"),
            ("Security", "security"),
            ("Code Quality", "code_quality"),
            ("Dependencies", "dependency"),
        ]:
            value = scores.get(key)
            score_table_data.append([label, f"{value:.1f}" if isinstance(value, (int, float)) else "No data"])
        score_table_data.append(["Risk Level", str(scores.get("risk_level") or "Unknown")])
        story.append(_styled_table(score_table_data))

        # Repository info
        story.append(Paragraph("Repository Information", h2))
        info_rows = [
            ["Owner", repo.get("owner") or "—"],
            ["Default branch", repo.get("default_branch") or "—"],
            ["Primary language", repo.get("primary_language") or "—"],
            ["Analyzed at", data["commit"].get("analyzed_at") or "—"],
        ]
        story.append(_styled_table([["Field", "Value"], *info_rows]))

        # Analyzer coverage
        story.append(Paragraph("Analyzer Coverage", h2))
        cov = data["analyzer_coverage"]
        coverage_pct = cov.get("coverage_percent")
        story.append(
            Paragraph(
                f"Executed: {cov['executed_count']} · Completed: {cov['completed_count']} · "
                f"Coverage: {coverage_pct if coverage_pct is not None else 'n/a'}%",
                body,
            ),
        )
        if cov["rows"]:
            rows = [["Analyzer", "Status", "Findings"]]
            for r in cov["rows"]:
                rows.append([r["analyzer"], r["status"], str(r.get("finding_count") if r.get("finding_count") is not None else "—")])
            story.append(_styled_table(rows))
        else:
            story.append(Paragraph("No analyzer summary recorded for the latest run.", muted))

        # Trend
        story.append(Paragraph("Historical Comparison", h2))
        trend = data["trend"]
        if trend.get("available"):
            story.append(
                Paragraph(
                    f"Compared to previous analysis on {trend['compared_to_captured_at']}: "
                    f"health {_fmt_delta(trend['health_score_delta'])}, "
                    f"security {_fmt_delta(trend['security_score_delta'])}, "
                    f"findings {_fmt_delta(trend['finding_count_delta'], invert=True)}.",
                    body,
                ),
            )
            story.append(Paragraph(trend["note"], muted))
        else:
            story.append(Paragraph(f"Not available: {trend.get('reason')}", muted))

        # Findings by category
        story.append(PageBreak())
        story.append(Paragraph("Findings", h2))
        findings = data["findings"]
        story.append(Paragraph(f"Total findings: {findings['total']}", body))
        for category, bucket in findings["by_category"].items():
            story.append(Paragraph(category.replace("_", " ").title(), ParagraphStyle("cat", parent=styles["Heading3"], spaceBefore=10)))
            counts = bucket["severity_counts"]
            story.append(
                Paragraph(
                    f"Critical: {counts['critical']} · High: {counts['high']} · "
                    f"Medium: {counts['medium']} · Low: {counts['low']}",
                    muted,
                ),
            )
            if bucket["items"]:
                rows = [["Severity", "Title", "File", "Line"]]
                for item in bucket["items"]:
                    rows.append(
                        [item["severity"], item["title"] or item["rule_id"] or "—", item["file"] or "—", str(item["line"] or "—")],
                    )
                story.append(_styled_table(rows, severity_col=0))
                if bucket["truncated"]:
                    story.append(Paragraph(f"...and {bucket['truncated']} more not shown in this report.", muted))
            else:
                story.append(Paragraph("No findings in this category.", muted))

        # Dependencies
        story.append(Paragraph("Dependency Vulnerabilities", h2))
        deps = data["dependencies"]
        story.append(Paragraph(f"Total dependencies scanned: {deps['total']} · Vulnerable: {deps['vulnerable_count']}", body))
        if deps["vulnerable_items"]:
            rows = [["Package", "Current", "Latest", "Severity", "Vulnerability"]]
            for d in deps["vulnerable_items"]:
                rows.append(
                    [d["package"], d["current_version"] or "—", d["latest_version"] or "—", d["severity"] or "—", (d["vulnerability"] or "—")[:60]],
                )
            story.append(_styled_table(rows, severity_col=3))
        else:
            story.append(Paragraph("No vulnerable dependencies detected among scanned packages.", muted))

        # Recommended actions
        story.append(Paragraph("Top Priority Fixes", h2))
        actions = data["recommended_actions"]
        if actions:
            for a in actions:
                story.append(Paragraph(f"• [{a['priority'].upper()}] {a['label']} — {a['description']}", body))
        else:
            story.append(Paragraph("No outstanding recommended actions.", muted))

        # Limitations
        story.append(Paragraph("Limitations", h2))
        for item in data["limitations"]:
            story.append(Paragraph(f"• {item}", muted))

        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                "Verion does not claim 100% accuracy for any static-analysis result. This report "
                "reflects evidence collected by the analyzers listed above, with their stated "
                "coverage and limitations.",
                muted,
            ),
        )

        doc.build(story)
        return buffer.getvalue()


def _severity_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in items:
        sev = item.get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts


def _finding_row(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": f.get("severity"),
        "title": f.get("title"),
        "rule_id": f.get("rule_id"),
        "file": f.get("file"),
        "line": f.get("line"),
        "status": f.get("status"),
    }


def _fmt_delta(value: float | None, *, invert: bool = False) -> str:
    if value is None:
        return "no data"
    if value == 0:
        return "no change"
    improved = (value > 0) if not invert else (value < 0)
    arrow = "↑" if value > 0 else "↓"
    label = "improved" if improved else "regressed"
    return f"{arrow} {abs(value):g} ({label})"


def _styled_table(rows: list[list[str]], severity_col: int | None = None) -> Table:
    table = Table(rows, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    if severity_col is not None:
        for row_idx in range(1, len(rows)):
            sev = str(rows[row_idx][severity_col]).lower()
            color = SEVERITY_COLORS.get(sev)
            if color:
                style.append(("TEXTCOLOR", (severity_col, row_idx), (severity_col, row_idx), color))
                style.append(("FONTNAME", (severity_col, row_idx), (severity_col, row_idx), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table
