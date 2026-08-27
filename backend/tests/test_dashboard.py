from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.core.database import get_database
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.services.dashboard import DashboardService
from app.services.repositories import RepositoryService
from tests.test_auth import _signup


@pytest.mark.asyncio
async def test_dashboard_includes_engineering_overview_fields(client):
    db = get_database()
    organization_id = str(ObjectId())
    repository_id = str(ObjectId())

    await db["analysis_runs"].insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "repository_id": repository_id,
            "status": "complete",
            "trigger": "manual",
            "created_at": datetime.now(UTC),
        },
    )
    await db["repositories"].insert_one(
        {
            "_id": ObjectId(repository_id),
            "organization_id": organization_id,
            "name": "payment-service",
            "full_name": "acme/payment-service",
            "owner": "acme",
            "health_score": 87.0,
            "security_score": 92.0,
            "code_quality_score": 81.0,
            "analysis_status": "complete",
        },
    )
    await db["pull_requests"].insert_one(
        {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "repository_name": "acme/payment-service",
            "github_id": 142,
            "title": "Improve authorization",
            "author": "dev",
            "risk_score": 70,
            "issues_count": 3,
            "status": "open",
            "created_at": datetime.now(UTC),
        },
    )
    await db["findings"].insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "repository_id": repository_id,
            "analysis_id": "run-1",
            "severity": "critical",
            "category": "security",
            "rule_id": "B105",
            "title": "Hardcoded password",
            "description": "Possible hardcoded password",
            "file": "app/config.py",
            "line": 8,
            "status": "open",
            "metadata": {},
            "created_at": datetime.now(UTC),
        },
    )

    service = _dashboard_service(db)
    response = await service.get_dashboard(organization_id)

    assert response.metrics.repository_health == 87.0
    assert response.metrics.security_score == 92.0
    assert response.metrics.code_quality_score == 81.0
    assert len(response.repository_health_items) == 1
    assert response.high_risk_changes[0].pull_request_id == 142
    assert response.security_severity_counts is not None
    assert response.security_severity_counts.critical == 1


@pytest.mark.asyncio
async def test_dashboard_summary_metrics_and_sections(client):
    db = get_database()
    organization_id = str(ObjectId())
    repository_id = str(ObjectId())

    await db["analysis_runs"].insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "repository_id": repository_id,
            "status": "complete",
            "trigger": "manual",
            "trigger_source": "manual",
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
    )
    await db["repositories"].insert_one(
        {
            "_id": ObjectId(repository_id),
            "organization_id": organization_id,
            "name": "api",
            "full_name": "acme/api",
            "owner": "acme",
            "health_score": 75.0,
            "security_score": 80.0,
            "code_quality_score": 70.0,
            "analysis_status": "complete",
            "open_pull_requests": 2,
        },
    )
    await db["pull_requests"].insert_one(
        {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "repository_name": "acme/api",
            "github_id": 55,
            "title": "Risky change",
            "risk_score": 72,
            "issues_count": 4,
            "status": "open",
            "risk_scored_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
    )
    await db["findings"].insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "repository_id": repository_id,
            "analysis_id": "run-1",
            "severity": "critical",
            "category": "security",
            "rule_id": "B105",
            "title": "Secret in code",
            "description": "Secret detected",
            "file": "app.py",
            "line": 1,
            "status": "open",
            "metadata": {},
            "created_at": datetime.now(UTC),
        },
    )

    summary = await _dashboard_service(db).get_dashboard_summary(organization_id)

    overview_keys = {item.key for item in summary.overview}
    assert "engineering_health" in overview_keys
    assert "critical_findings" in overview_keys

    health_metric = next(item for item in summary.overview if item.key == "engineering_health")
    assert health_metric.value == 75.0

    critical_metric = next(item for item in summary.overview if item.key == "critical_findings")
    assert critical_metric.value == 1

    assert summary.health.score == 75.0
    assert summary.security.total == 1
    assert summary.pull_requests.high_risk[0].verdict == "critical_risk"
    assert len(summary.analysis_activity) == 1
    assert summary.risk_distribution.has_data is True
    assert summary.trends.available is False
    assert summary.recommended_actions


@pytest.mark.asyncio
async def test_dashboard_summary_empty_workspace(client):
    db = get_database()
    organization_id = str(ObjectId())
    summary = await _dashboard_service(db).get_dashboard_summary(organization_id)

    assert summary.has_analysis_data is False
    assert summary.overview[0].value is None
    assert summary.health.score is None
    assert summary.security.has_data is False
    assert summary.risk_distribution.has_data is False
    assert any(action.id == "connect-repo" for action in summary.recommended_actions)


@pytest.mark.asyncio
async def test_dashboard_summary_failed_analysis_attention(client):
    db = get_database()
    organization_id = str(ObjectId())
    repository_id = str(ObjectId())

    await db["analysis_runs"].insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "repository_id": repository_id,
            "status": "complete",
            "trigger": "manual",
            "created_at": datetime.now(UTC),
        },
    )
    await db["repositories"].insert_one(
        {
            "_id": ObjectId(repository_id),
            "organization_id": organization_id,
            "name": "worker",
            "full_name": "acme/worker",
            "analysis_status": "failed",
            "updated_at": datetime.now(UTC),
        },
    )

    summary = await _dashboard_service(db).get_dashboard_summary(organization_id)
    assert any(item.entity_type == "repository" and "failed" in item.title.lower() for item in summary.attention)


@pytest.mark.asyncio
async def test_dashboard_summary_organization_isolation(client):
    await _signup(client, "orga-dash@acme.dev")
    me = await client.get("/api/v1/auth/me")
    org_a = me.json()["organization"]["id"]

    db = get_database()
    repo_b = str(ObjectId())
    await db.repositories.insert_one(
        {
            "_id": ObjectId(repo_b),
            "organization_id": str(ObjectId()),
            "name": "other",
            "full_name": "other/secret",
            "health_score": 10.0,
            "analysis_status": "complete",
        },
    )
    await db.analysis_runs.insert_one(
        {
            "_id": ObjectId(),
            "organization_id": org_a,
            "repository_id": str(ObjectId()),
            "status": "complete",
            "created_at": datetime.now(UTC),
        },
    )

    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    repo_names = [item["name"] for item in data["repositories"]]
    assert "other/secret" not in repo_names


def _dashboard_service(db):
    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)
    return DashboardService(
        repo_repo,
        pr_repo,
        RepositoryService(repo_repo, pr_repo),
        FindingRepository(db),
        AnalysisRunRepository(db),
        DependencyRepository(db),
    )
