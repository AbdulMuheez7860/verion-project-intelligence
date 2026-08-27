import pytest
from httpx import AsyncClient

from app.core.database import get_database
from tests.test_auth import _signup


async def _insert_repository(client: AsyncClient, *, name: str = "api", owner: str = "acme") -> str:
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    result = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": hash(name) % 1_000_000,
            "name": name,
            "owner": owner,
            "full_name": f"{owner}/{name}",
            "default_branch": "main",
            "private": False,
            "open_pull_requests": 2,
            "analysis_status": "complete",
            "health_score": 85.0,
            "security_score": 90.0,
            "code_quality_score": 78.0,
            "dependency_score": 88.0,
            "risk_level": "low",
            "risk_rank": 1,
            "security_finding_count": 1,
            "quality_finding_count": 3,
            "dependency_status": "healthy",
            "last_analyzed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    return str(result.inserted_id)


@pytest.mark.asyncio
async def test_repository_list_search_and_sort(client: AsyncClient):
    await _signup(client, "repo-list@acme.dev")
    await _insert_repository(client, name="alpha", owner="acme")
    await _insert_repository(client, name="beta", owner="acme")

    search = await client.get("/api/v1/repositories", params={"q": "alpha"})
    assert search.status_code == 200
    body = search.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "alpha"

    sorted_health = await client.get(
        "/api/v1/repositories",
        params={"sort": "health", "order": "desc", "pageSize": 10},
    )
    assert sorted_health.status_code == 200
    scores = [item.get("healthScore") for item in sorted_health.json()["items"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_repository_list_filters(client: AsyncClient):
    await _signup(client, "repo-filter@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    await db.repositories.update_one(
        {"_id": __import__("bson").ObjectId(repo_id)},
        {"$set": {"analysis_status": "failed", "risk_level": "high", "risk_rank": 3, "security_score": 40}},
    )

    response = await client.get(
        "/api/v1/repositories",
        params={"analysisStatus": "failed", "riskLevel": "high", "securityStatus": "poor"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_repository_intelligence_endpoint(client: AsyncClient):
    await _signup(client, "repo-intel@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    await db.findings.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "analysis_id": "run-1",
            "severity": "critical",
            "category": "security",
            "rule_id": "rule-1",
            "title": "SQL injection risk",
            "description": "unsafe query",
            "file": "app/db.py",
            "line": 10,
            "confidence": 0.9,
            "status": "open",
            "metadata": {},
        },
    )

    response = await client.get(f"/api/v1/repositories/{repo_id}/intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["repository"]["id"] == repo_id
    assert body["health"]["hasCompletedAnalysis"] is True
    assert body["securitySummary"]["severityCounts"]["critical"] == 1


@pytest.mark.asyncio
async def test_repository_scoped_findings_pagination(client: AsyncClient):
    await _signup(client, "repo-findings@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    for index in range(3):
        await db.findings.insert_one(
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-1",
                "severity": "high",
                "category": "security",
                "rule_id": f"rule-{index}",
                "title": f"Finding {index}",
                "description": "issue",
                "file": "app/main.py",
                "line": index + 1,
                "confidence": 0.8,
                "status": "open",
                "metadata": {},
            },
        )

    response = await client.get(
        f"/api/v1/repositories/{repo_id}/findings",
        params={"category": "security", "page": 1, "pageSize": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["hasNext"] is True


@pytest.mark.asyncio
async def test_repository_dependencies_and_pull_requests(client: AsyncClient):
    await _signup(client, "repo-deps@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    await db.dependencies.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "analysis_id": "run-1",
            "package_name": "requests",
            "current_version": "2.31.0",
            "latest_version": "2.32.0",
            "status": "outdated",
            "vulnerability": None,
            "license": "Apache-2.0",
        },
    )
    await db.pull_requests.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "repository_name": "acme/api",
            "github_id": 101,
            "title": "Fix auth",
            "author": "dev",
            "risk_score": 55,
            "files_changed": 4,
            "issues_count": 2,
            "status": "open",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-02T00:00:00+00:00",
        },
    )

    deps = await client.get(f"/api/v1/repositories/{repo_id}/dependencies")
    assert deps.status_code == 200
    assert deps.json()["total"] == 1

    prs = await client.get(f"/api/v1/repositories/{repo_id}/pull-requests")
    assert prs.status_code == 200
    pr_body = prs.json()
    assert pr_body["total"] == 1
    assert pr_body["items"][0]["verdict"] == "high_risk"


@pytest.mark.asyncio
async def test_analysis_run_detail_and_history(client: AsyncClient):
    await _signup(client, "repo-runs@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    run = await db.analysis_runs.insert_one(
        {
            "repository_id": repo_id,
            "organization_id": org_id,
            "status": "complete",
            "trigger": "manual",
            "trigger_source": "manual",
            "commit_sha": "abc123",
            "branch": "main",
            "finding_count": 5,
            "health_snapshot": {
                "health_score": 85.0,
                "security_score": 90.0,
                "code_quality_score": 78.0,
                "dependency_score": 88.0,
                "risk_level": "low",
                "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 2},
            },
            "analyzer_summary": {
                "executed": ["semgrep", "bandit"],
                "dependency_scan": True,
                "repository_metrics_status": "completed",
            },
            "started_at": __import__("datetime").datetime(2026, 1, 1, 0, 0, 0),
            "completed_at": __import__("datetime").datetime(2026, 1, 1, 0, 5, 0),
            "created_at": __import__("datetime").datetime(2026, 1, 1, 0, 0, 0),
        },
    )
    run_id = str(run.inserted_id)

    detail = await client.get(f"/api/v1/repositories/{repo_id}/analysis-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["commitSha"] == "abc123"
    assert detail.json()["analyzerSummary"]["executed"] == ["semgrep", "bandit"]
    # Regression test: analyzer_summary must be a *typed* model, not a raw
    # passthrough dict - a raw dict field is never camelCased by Pydantic's
    # alias_generator, so `dependency_scan` / `repository_metrics_status`
    # would previously arrive as snake_case and this assertion would fail.
    assert detail.json()["analyzerSummary"]["dependencyScan"] is True
    assert detail.json()["analyzerSummary"]["repositoryMetricsStatus"] == "completed"

    history = await client.get(f"/api/v1/repositories/{repo_id}/health-history")
    assert history.status_code == 200
    assert history.json()["hasSufficientHistory"] is False


@pytest.mark.asyncio
async def test_analyze_prevents_duplicate_queue(client: AsyncClient):
    await _signup(client, "repo-analyze@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    await db.repositories.update_one(
        {"_id": __import__("bson").ObjectId(repo_id)},
        {"$set": {"analysis_status": "running"}},
    )

    response = await client.post(f"/api/v1/repositories/{repo_id}/analyze")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_viewer_cannot_analyze_repository(client: AsyncClient):
    await _signup(client, "repo-viewer@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    await db.memberships.update_one(
        {"user_id": me.json()["user"]["id"], "organization_id": me.json()["organization"]["id"]},
        {"$set": {"role": "viewer"}},
    )

    response = await client.post(f"/api/v1/repositories/{repo_id}/analyze")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_finding_detail_org_isolation(client: AsyncClient):
    await _signup(client, "finding-a@acme.dev")
    repo_id = await _insert_repository(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    finding = await db.findings.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "analysis_id": "run-1",
            "severity": "high",
            "category": "secret",
            "rule_id": "secret-1",
            "title": "Leaked token",
            "description": "api_key=super-secret-value",
            "file": "config.py",
            "line": 3,
            "confidence": 1.0,
            "status": "open",
            "metadata": {},
        },
    )
    finding_id = str(finding.inserted_id)

    detail = await client.get(f"/api/v1/findings/{finding_id}")
    assert detail.status_code == 200
    assert "REDACTED" in (detail.json().get("description") or "")

    await client.post("/api/v1/auth/logout")
    await _signup(client, "finding-b@acme.dev", team="Finding B Org")
    isolated = await client.get(f"/api/v1/findings/{finding_id}")
    assert isolated.status_code == 404
