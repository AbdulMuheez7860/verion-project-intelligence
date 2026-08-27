import pytest
from httpx import AsyncClient

from app.core.database import get_database
from tests.test_auth import _signup


async def _insert_pull_request(client: AsyncClient, *, risk_score: int = 72, verdict: str = "critical_risk") -> int:
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 88001,
            "name": "api",
            "owner": "acme",
            "full_name": "acme/api",
            "analysis_status": "complete",
            "health_score": 80.0,
            "security_score": 85.0,
            "code_quality_score": 78.0,
            "risk_level": "medium",
            "last_analyzed_at": __import__("datetime").datetime(2026, 1, 2, 0, 0, 0),
        },
    )
    pr_id = 900001
    await db.pull_requests.insert_one(
        {
            "organization_id": org_id,
            "repository_id": str(repo.inserted_id),
            "repository_name": "acme/api",
            "github_id": pr_id,
            "number": 42,
            "title": "Fix auth middleware",
            "author": "dev",
            "status": "open",
            "draft": False,
            "risk_score": risk_score,
            "risk_level": "critical" if risk_score >= 70 else "high",
            "verdict": verdict,
            "security_issues_count": 2,
            "quality_issues_count": 1,
            "dependency_issues_count": 1,
            "issues_count": 4,
            "files_changed": 5,
            "changed_files": ["app/auth.py", "requirements.txt"],
            "file_details": [
                {
                    "path": "app/auth.py",
                    "status": "modified",
                    "additions": 20,
                    "deletions": 3,
                    "category": "security",
                },
                {
                    "path": "requirements.txt",
                    "status": "modified",
                    "additions": 1,
                    "deletions": 0,
                    "category": "dependencies",
                },
            ],
            "risk_score_detail": {
                "value": risk_score,
                "level": "critical",
                "engine": "Verion Risk Engine",
                "factors": [
                    {
                        "label": "Security findings",
                        "contribution": 25,
                        "explanation": "2 finding(s) in this change (1 high, 1 medium).",
                    },
                ],
            },
            "created_at": __import__("datetime").datetime(2026, 1, 1, 0, 0, 0),
            "updated_at": __import__("datetime").datetime(2026, 1, 2, 0, 0, 0),
            "risk_scored_at": __import__("datetime").datetime(2026, 1, 2, 0, 0, 0),
            "head_sha": "abc123",
            "base_sha": "def456",
        },
    )
    return pr_id


@pytest.mark.asyncio
async def test_pull_request_list_pagination_and_filters(client: AsyncClient):
    await _signup(client, "pr-list@acme.dev")
    pr_id = await _insert_pull_request(client)

    response = await client.get(
        "/api/v1/pull-requests",
        params={"verdict": "critical_risk", "page": 1, "pageSize": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == pr_id
    assert body["items"][0]["verdict"] == "critical_risk"
    assert body["items"][0]["securityImpact"] == 2


@pytest.mark.asyncio
async def test_pull_request_search(client: AsyncClient):
    await _signup(client, "pr-search@acme.dev")
    await _insert_pull_request(client)

    response = await client.get("/api/v1/pull-requests", params={"q": "auth middleware"})
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_pull_request_intelligence(client: AsyncClient):
    await _signup(client, "pr-intel@acme.dev")
    pr_id = await _insert_pull_request(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    pr_doc = await db.pull_requests.find_one({"github_id": pr_id, "organization_id": org_id})
    repo_id = pr_doc["repository_id"]

    await db.findings.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "analysis_id": "run-1",
            "severity": "critical",
            "category": "security",
            "rule_id": "bandit-1",
            "title": "Unsafe auth pattern",
            "description": "Potential auth bypass",
            "file": "app/auth.py",
            "line": 12,
            "confidence": 0.9,
            "status": "open",
            "metadata": {},
        },
    )

    response = await client.get(f"/api/v1/pull-requests/{pr_id}/intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["mergeSafety"]["label"] == "BLOCKED"
    assert body["riskScoreDetail"]["factors"][0]["contribution"] == 25
    assert len(body["changedFiles"]) == 2
    assert body["impactCounts"]["security"] >= 1
    assert any(rec["priority"] == "high" for rec in body["recommendations"])


@pytest.mark.asyncio
async def test_pull_request_organization_isolation(client: AsyncClient):
    await _signup(client, "pr-orga@acme.dev")
    pr_id = await _insert_pull_request(client)

    await _signup(client, "pr-orgb@acme.dev", team="Org B PR")
    response = await client.get(f"/api/v1/pull-requests/{pr_id}/intelligence")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_viewer_cannot_reanalyze_pull_request(client: AsyncClient):
    await _signup(client, "pr-viewer@acme.dev")
    pr_id = await _insert_pull_request(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    await db.memberships.update_one(
        {"user_id": me.json()["user"]["id"], "organization_id": me.json()["organization"]["id"]},
        {"$set": {"role": "viewer"}},
    )

    response = await client.post(f"/api/v1/pull-requests/{pr_id}/reanalyze")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pr_freshness_stale_when_pr_updated_after_scoring(client: AsyncClient):
    await _signup(client, "pr-stale@acme.dev")
    pr_id = await _insert_pull_request(client)
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    await db.pull_requests.update_one(
        {"github_id": pr_id, "organization_id": org_id},
        {"$set": {"updated_at": __import__("datetime").datetime(2026, 1, 3, 0, 0, 0)}},
    )

    response = await client.get(f"/api/v1/pull-requests/{pr_id}/intelligence")
    assert response.status_code == 200
    assert response.json()["freshness"]["isStale"] is True
    assert response.json()["freshness"]["status"] == "pr_changed"
