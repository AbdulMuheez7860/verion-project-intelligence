import pytest
from httpx import AsyncClient

from app.core.database import get_database
from tests.test_auth import _signup
from tests.test_repositories import _insert_repository


async def _insert_analysis_run(
    *,
    org_id: str,
    repo_id: str,
    status: str = "complete",
    trigger: str = "manual",
    commit_sha: str = "abc123def456",
    error: str | None = None,
) -> str:
    from datetime import UTC, datetime

    from bson import ObjectId

    db = get_database()
    now = datetime.now(UTC)
    doc = {
        "_id": ObjectId(),
        "organization_id": org_id,
        "repository_id": repo_id,
        "status": status,
        "trigger": trigger,
        "trigger_source": trigger,
        "commit_sha": commit_sha,
        "branch": "main",
        "started_at": now,
        "completed_at": now if status in {"complete", "failed"} else None,
        "finding_count": 5 if status == "complete" else 0,
        "error": error,
        "analyzer_summary": {"executed": ["ruff"], "skipped": [], "failed": [], "dependency_scan": False},
        "health_snapshot": {
            "health_score": 82.0,
            "security_score": 90.0,
            "code_quality_score": 78.0,
            "dependency_score": 85.0,
        },
        "created_at": now,
    }
    result = await db.analysis_runs.insert_one(doc)
    return str(result.inserted_id)


@pytest.mark.asyncio
async def test_list_analysis_runs_paginated(client: AsyncClient):
    await _signup(client, "runs-list@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="complete")
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="failed", error="clone failed")

    response = await client.get("/api/v1/analysis-runs", params={"page": 1, "pageSize": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["repositoryName"] == "acme/api"


@pytest.mark.asyncio
async def test_list_analysis_runs_status_filter(client: AsyncClient):
    await _signup(client, "runs-status@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="complete")
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="failed", error="err")

    response = await client.get("/api/v1/analysis-runs", params={"status": "failed"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "failed"


@pytest.mark.asyncio
async def test_list_analysis_runs_trigger_filter(client: AsyncClient):
    await _signup(client, "runs-trigger@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, trigger="manual")
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, trigger="webhook:push")

    manual = await client.get("/api/v1/analysis-runs", params={"trigger": "manual"})
    assert manual.status_code == 200
    assert manual.json()["total"] == 1

    webhook = await client.get("/api/v1/analysis-runs", params={"trigger": "webhook"})
    assert webhook.status_code == 200
    assert webhook.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_analysis_runs_repository_filter(client: AsyncClient):
    await _signup(client, "runs-repo@acme.dev")
    repo_a = await _insert_repository(client, name="alpha")
    repo_b = await _insert_repository(client, name="beta")
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await _insert_analysis_run(org_id=org_id, repo_id=repo_a)
    await _insert_analysis_run(org_id=org_id, repo_id=repo_b)

    response = await client.get("/api/v1/analysis-runs", params={"repositoryId": repo_a})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["repositoryId"] == repo_a


@pytest.mark.asyncio
async def test_list_analysis_runs_commit_search(client: AsyncClient):
    await _signup(client, "runs-search@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await _insert_analysis_run(org_id=org_id, repo_id=repo_id, commit_sha="deadbeef1234")

    response = await client.get("/api/v1/analysis-runs", params={"q": "deadbeef"})
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_analysis_run_detail(client: AsyncClient):
    await _signup(client, "runs-detail@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    run_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id)

    response = await client.get(f"/api/v1/analysis-runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["repositoryName"] == "acme/api"
    assert body["healthSnapshot"]["health_score"] == 82.0
    assert body["analyzerSummary"]["executed"] == ["ruff"]
    assert body["capabilities"]["canRetry"] is False


@pytest.mark.asyncio
async def test_get_analysis_run_detail_with_snapshot(client: AsyncClient):
    await _signup(client, "runs-snapshot@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    run_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id)

    db = get_database()
    from datetime import UTC, datetime

    from bson import ObjectId

    await db.analysis_snapshots.insert_one(
        {
            "_id": ObjectId(),
            "organization_id": org_id,
            "repository_id": repo_id,
            "analysis_run_id": run_id,
            "captured_at": datetime.now(UTC),
            "health_score": 82.0,
            "security_score": 90.0,
            "quality_score": 78.0,
            "dependency_score": 85.0,
            "pr_risk_score": 30.0,
        },
    )

    response = await client.get(f"/api/v1/analysis-runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["snapshot"]["id"]
    assert response.json()["analyticsHref"]


@pytest.mark.asyncio
async def test_analysis_runs_organization_isolation(client: AsyncClient):
    await _signup(client, "runs-org-a@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    run_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id)

    await _signup(client, "runs-org-b@acme.dev", team="Other Org")
    response = await client.get(f"/api/v1/analysis-runs/{run_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_failed_analysis_run(client: AsyncClient, monkeypatch):
    await _signup(client, "runs-retry@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    run_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="failed", error="timeout")

    enqueued: list[str] = []

    def fake_enqueue(repository_id: str, organization_id: str, *, trigger: str = "manual", analysis_run_id=None):
        enqueued.append(repository_id)

    monkeypatch.setattr("app.workers.tasks.analysis.enqueue_analysis", fake_enqueue)

    response = await client.post(f"/api/v1/analysis-runs/{run_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert enqueued == [repo_id]


@pytest.mark.asyncio
async def test_viewer_cannot_retry_analysis_run(client: AsyncClient):
    await _signup(client, "runs-viewer@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    user_id = me.json()["user"]["id"]
    run_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="failed", error="err")

    db = get_database()
    await db.memberships.update_one(
        {"user_id": user_id, "organization_id": org_id},
        {"$set": {"role": "viewer"}},
    )

    response = await client.post(f"/api/v1/analysis-runs/{run_id}/retry")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cancel_queued_analysis_run(client: AsyncClient):
    await _signup(client, "runs-cancel@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    db = get_database()
    from datetime import UTC, datetime

    from bson import ObjectId

    run_id = str(
        (
            await db.analysis_runs.insert_one(
                {
                    "_id": ObjectId(),
                    "organization_id": org_id,
                    "repository_id": repo_id,
                    "status": "queued",
                    "trigger": "manual",
                    "trigger_source": "manual",
                    "created_at": datetime.now(UTC),
                },
            )
        ).inserted_id,
    )
    await db.repositories.update_one(
        {"_id": ObjectId(repo_id)},
        {"$set": {"analysis_status": "queued"}},
    )

    response = await client.post(f"/api/v1/analysis-runs/{run_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    doc = await db.analysis_runs.find_one({"_id": ObjectId(run_id)})
    assert doc["status"] == "failed"
    assert doc["error"] == "Cancelled by user."


@pytest.mark.asyncio
async def test_cannot_cancel_running_analysis_run(client: AsyncClient):
    await _signup(client, "runs-cancel-running@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    run_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="running")

    response = await client.post(f"/api/v1/analysis-runs/{run_id}/cancel")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_retry_blocked_when_active_run_exists(client: AsyncClient, monkeypatch):
    await _signup(client, "runs-dup@acme.dev")
    repo_id = await _insert_repository(client)
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    failed_id = await _insert_analysis_run(org_id=org_id, repo_id=repo_id, status="failed", error="err")

    db = get_database()
    from datetime import UTC, datetime

    from bson import ObjectId

    await db.analysis_runs.insert_one(
        {
            "_id": ObjectId(),
            "organization_id": org_id,
            "repository_id": repo_id,
            "status": "running",
            "trigger": "manual",
            "trigger_source": "manual",
            "started_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
    )

    response = await client.post(f"/api/v1/analysis-runs/{failed_id}/retry")
    assert response.status_code == 409
