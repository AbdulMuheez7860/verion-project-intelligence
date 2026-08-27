import pytest
from httpx import AsyncClient

from app.core.database import get_database
from app.lib.historical_helpers import compare_metric, is_material_improvement, is_material_regression
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.services.analysis_snapshot_service import AnalysisSnapshotService
from app.services.historical_intelligence import HistoricalIntelligenceService
from tests.test_auth import _signup


async def _insert_snapshot(
    db,
    *,
    organization_id: str,
    repository_id: str,
    analysis_run_id: str,
    captured_at=None,
    health_score: float,
    security_score: float = 80.0,
    quality_score: float = 75.0,
    dependency_score: float = 85.0,
    finding_critical: int = 0,
) -> None:
    if captured_at is None:
        captured_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    await db.analysis_snapshots.insert_one(
        {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "analysis_run_id": analysis_run_id,
            "captured_at": captured_at,
            "health_score": health_score,
            "security_score": security_score,
            "quality_score": quality_score,
            "dependency_score": dependency_score,
            "pr_risk_score": 40.0,
            "finding_counts": {
                "total": finding_critical,
                "critical": finding_critical,
                "high": 0,
                "medium": 0,
                "low": 0,
            },
            "security_findings": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "quality_findings": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "dependency_findings": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "dependency_counts": {"total": 0, "vulnerable": 0, "outdated": 0, "healthy": 0},
            "pull_request_metrics": {"open": 0, "high_risk": 0, "critical_risk": 0, "average_risk_score": 40.0},
            "analyzer_summary": {"executed": ["semgrep"]},
            "created_at": captured_at,
        },
    )


@pytest.mark.asyncio
async def test_snapshot_create_idempotent():
    db = get_database()
    repo = AnalysisSnapshotRepository(db)
    service = AnalysisSnapshotService(repo)
    org_id = "org-1"
    repo_id = "repo-1"
    run_id = "run-1"

    first = await service.create_from_analysis(
        organization_id=org_id,
        repository_id=repo_id,
        analysis_run_id=run_id,
        commit_sha="abc",
        branch="main",
        captured_at=__import__("datetime").datetime(2026, 3, 1, 12, 0, 0, tzinfo=__import__("datetime").UTC),
        health_score=80.0,
        security_score=85.0,
        quality_score=78.0,
        dependency_score=90.0,
        pr_risk_score=30.0,
        stored_findings=[],
        dep_counts={"total": 0, "vulnerable": 0, "outdated": 0, "healthy": 0},
        pull_request_metrics={"open": 0, "high_risk": 0, "critical_risk": 0, "average_risk_score": 30.0},
        analyzer_summary={"executed": ["semgrep"]},
    )
    second = await service.create_from_analysis(
        organization_id=org_id,
        repository_id=repo_id,
        analysis_run_id=run_id,
        commit_sha="abc",
        branch="main",
        captured_at=__import__("datetime").datetime(2026, 3, 1, 12, 0, 0, tzinfo=__import__("datetime").UTC),
        health_score=50.0,
        security_score=50.0,
        quality_score=50.0,
        dependency_score=50.0,
        pr_risk_score=50.0,
        stored_findings=[],
        dep_counts={"total": 0, "vulnerable": 0, "outdated": 0, "healthy": 0},
        pull_request_metrics={"open": 0, "high_risk": 0, "critical_risk": 0, "average_risk_score": 50.0},
        analyzer_summary={"executed": ["semgrep"]},
    )
    assert first is not None
    assert second is not None
    assert first["id"] == second["id"]
    assert first["health_score"] == 80.0


def test_compare_metric_zero_previous_no_percentage():
    result = compare_metric(metric="health_score", current=80, previous=0, label="Health")
    assert result["delta"] == 80
    assert result["percentage_change"] is None


def test_compare_metric_security_findings_lower_is_better():
    result = compare_metric(metric="finding_critical", current=1, previous=3, label="Critical")
    assert result["direction"] == "improved"
    assert is_material_improvement("finding_critical", result["delta"])
    assert not is_material_regression("finding_critical", result["delta"])


def test_compare_metric_health_drop_is_regression():
    result = compare_metric(metric="health_score", current=65, previous=80, label="Health")
    assert result["direction"] == "worsened"
    assert is_material_regression("health_score", result["delta"])


@pytest.mark.asyncio
async def test_analytics_overview_zero_snapshots(client: AsyncClient):
    await _signup(client, "analytics-zero@acme.dev")
    response = await client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["baseline"]["snapshotCount"] == 0
    assert payload["baseline"]["status"] == "building"
    assert payload["healthTrend"] == []


@pytest.mark.asyncio
async def test_analytics_overview_one_snapshot_established(client: AsyncClient):
    await _signup(client, "analytics-one@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 99010,
            "name": "api",
            "owner": "acme",
            "full_name": "acme/api",
            "analysis_status": "complete",
            "health_score": 80.0,
            "last_analyzed_at": __import__("datetime").datetime(2026, 3, 1, 12, 0, 0),
        },
    )
    repo_id = str(repo.inserted_id)
    dt = __import__("datetime")
    now = dt.datetime.now(dt.UTC)
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=repo_id,
        analysis_run_id="run-1",
        captured_at=now,
        health_score=80.0,
    )

    response = await client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["baseline"]["snapshotCount"] == 1
    assert payload["baseline"]["status"] == "established"
    assert len(payload["healthTrend"]) == 1
    assert payload["repositoryComparisons"][0]["trendDirection"] == "unavailable"


@pytest.mark.asyncio
async def test_analytics_overview_trend_with_multiple_snapshots(client: AsyncClient):
    await _signup(client, "analytics-trend@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 99011,
            "name": "web",
            "owner": "acme",
            "full_name": "acme/web",
            "analysis_status": "complete",
            "health_score": 88.0,
            "last_analyzed_at": __import__("datetime").datetime(2026, 3, 5, 12, 0, 0),
        },
    )
    repo_id = str(repo.inserted_id)
    dt = __import__("datetime")
    now = dt.datetime.now(dt.UTC)
    earlier = now - dt.timedelta(days=7)
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=repo_id,
        analysis_run_id="run-a",
        captured_at=earlier,
        health_score=70.0,
        finding_critical=2,
    )
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=repo_id,
        analysis_run_id="run-b",
        captured_at=now,
        health_score=88.0,
        finding_critical=0,
    )

    response = await client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["baseline"]["status"] == "trending"
    assert len(payload["healthTrend"]) == 2
    assert payload["healthTrend"][0]["value"] == 70.0
    assert payload["healthTrend"][1]["value"] == 88.0
    assert any(item["direction"] == "improved" for item in payload["improvements"])


@pytest.mark.asyncio
async def test_analytics_overview_repository_filter(client: AsyncClient):
    await _signup(client, "analytics-filter@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo_a = await db.repositories.insert_one(
        {"organization_id": org_id, "github_id": 1, "name": "a", "owner": "acme", "full_name": "acme/a"},
    )
    repo_b = await db.repositories.insert_one(
        {"organization_id": org_id, "github_id": 2, "name": "b", "owner": "acme", "full_name": "acme/b"},
    )
    dt = __import__("datetime")
    now = dt.datetime.now(dt.UTC)
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=str(repo_a.inserted_id),
        analysis_run_id="run-a1",
        captured_at=now,
        health_score=70.0,
    )
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=str(repo_b.inserted_id),
        analysis_run_id="run-b1",
        captured_at=now,
        health_score=90.0,
    )

    response = await client.get(f"/api/v1/analytics/overview?repositoryId={repo_a.inserted_id}")
    assert response.status_code == 200
    assert len(response.json()["healthTrend"]) == 1
    assert response.json()["healthTrend"][0]["value"] == 70.0


@pytest.mark.asyncio
async def test_analytics_organization_isolation(client: AsyncClient):
    await _signup(client, "analytics-iso@acme.dev", team="Iso Org")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {"organization_id": org_id, "github_id": 3, "name": "x", "owner": "acme", "full_name": "acme/x"},
    )
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=str(repo.inserted_id),
        analysis_run_id="run-x",
        captured_at=__import__("datetime").datetime(2026, 3, 1, tzinfo=__import__("datetime").UTC),
        health_score=75.0,
    )

    await _signup(client, "analytics-iso-other@acme.dev", team="Other Org")
    response = await client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    assert response.json()["baseline"]["snapshotCount"] == 0


@pytest.mark.asyncio
async def test_legacy_analytics_summary_uses_snapshot_count(client: AsyncClient):
    await _signup(client, "analytics-legacy@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await db.analysis_runs.insert_one(
        {
            "organization_id": org_id,
            "repository_id": "repo-legacy",
            "status": "complete",
            "trigger": "manual",
            "created_at": __import__("datetime").datetime(2026, 3, 1, tzinfo=__import__("datetime").UTC),
        },
    )
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 4,
            "name": "legacy",
            "owner": "acme",
            "full_name": "acme/legacy",
            "health_score": 82.0,
            "security_score": 88.0,
            "code_quality_score": 76.0,
        },
    )
    await _insert_snapshot(
        db,
        organization_id=org_id,
        repository_id=str(repo.inserted_id),
        analysis_run_id="run-legacy",
        captured_at=__import__("datetime").datetime(2026, 3, 1, tzinfo=__import__("datetime").UTC),
        health_score=82.0,
    )

    response = await client.get("/api/v1/analytics?range=30d")
    assert response.status_code == 200
    payload = response.json()
    assert payload["hasAnalysisData"] is True
    assert payload["analysisRunsCount"] == 1
