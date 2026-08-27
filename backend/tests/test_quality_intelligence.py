import pytest
from httpx import AsyncClient

from app.core.database import get_database
from tests.test_auth import _signup


async def _seed_quality_workspace(client: AsyncClient) -> tuple[str, str]:
    await _signup(client, "cq-intel@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 88002,
            "name": "web",
            "owner": "acme",
            "full_name": "acme/web",
            "analysis_status": "complete",
            "health_score": 78.0,
            "security_score": 90.0,
            "code_quality_score": 62.0,
            "risk_level": "medium",
            "last_analyzed_at": __import__("datetime").datetime(2026, 2, 2, 12, 0, 0),
        },
    )
    repo_id = str(repo.inserted_id)
    await db.analysis_runs.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "status": "complete",
            "trigger": "manual",
            "trigger_source": "manual",
            "completed_at": __import__("datetime").datetime(2026, 2, 2, 12, 0, 0),
            "created_at": __import__("datetime").datetime(2026, 2, 2, 11, 0, 0),
            "finding_count": 4,
            "analyzer_summary": {"executed": ["ruff", "eslint", "semgrep"]},
        },
    )
    await db.findings.insert_many(
        [
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-q1",
                "severity": "high",
                "category": "quality",
                "rule_id": "RUF001",
                "title": "Unused import detected",
                "description": "Import is not used",
                "file": "src/app.tsx",
                "line": 3,
                "confidence": 1.0,
                "status": "open",
                "metadata": {"engine": "ruff"},
                "created_at": __import__("datetime").datetime(2026, 2, 2, 12, 0, 0),
            },
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-q1",
                "severity": "medium",
                "category": "quality",
                "rule_id": "RUF001",
                "title": "Unused variable",
                "description": "Variable assigned but never used",
                "file": "src/utils.ts",
                "line": 12,
                "confidence": 1.0,
                "status": "open",
                "metadata": {"engine": "ruff"},
                "created_at": __import__("datetime").datetime(2026, 2, 2, 12, 0, 0),
            },
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-q1",
                "severity": "low",
                "category": "quality",
                "rule_id": "eslint/no-console",
                "title": "Unexpected console statement",
                "description": "Unexpected console usage",
                "file": "src/main.ts",
                "line": 8,
                "confidence": 1.0,
                "status": "open",
                "metadata": {"engine": "eslint"},
                "created_at": __import__("datetime").datetime(2026, 2, 2, 12, 0, 0),
            },
        ],
    )
    return org_id, repo_id


@pytest.mark.asyncio
async def test_quality_intelligence_payload(client: AsyncClient):
    await _seed_quality_workspace(client)

    response = await client.get("/api/v1/findings/code-quality/intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["hasAnalysisData"] is True
    assert body["posture"]["label"] == "ELEVATED DEBT"
    assert body["totals"]["open"] == 3
    assert body["totals"]["high"] == 1
    assert len(body["topRules"]) >= 1
    assert body["topRules"][0]["ruleId"] == "RUF001"
    assert "ruff" in body["scannerCoverage"]["executed"]
    assert len(body["unavailableMetrics"]) == 4
    assert len(body["recommendations"]) >= 1


@pytest.mark.asyncio
async def test_quality_intelligence_empty_workspace(client: AsyncClient):
    await _signup(client, "cq-empty@acme.dev")
    response = await client.get("/api/v1/findings/quality/intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["hasAnalysisData"] is False
    assert body["posture"]["label"] == "NOT ASSESSED"
    assert len(body["unavailableMetrics"]) == 4


@pytest.mark.asyncio
async def test_quality_findings_pagination_and_filters(client: AsyncClient):
    _org_id, repo_id = await _seed_quality_workspace(client)

    response = await client.get(
        "/api/v1/findings/quality/findings",
        params={"severity": "high", "repositoryId": repo_id, "page": 1, "pageSize": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Unused import detected"


@pytest.mark.asyncio
async def test_quality_findings_search_and_rule_filter(client: AsyncClient):
    await _seed_quality_workspace(client)

    search = await client.get("/api/v1/findings/quality/findings", params={"q": "console"})
    assert search.status_code == 200
    assert search.json()["total"] == 1

    rule = await client.get("/api/v1/findings/quality/findings", params={"ruleId": "RUF001"})
    assert rule.status_code == 200
    assert rule.json()["total"] == 2


@pytest.mark.asyncio
async def test_quality_findings_sort_by_severity(client: AsyncClient):
    await _seed_quality_workspace(client)

    response = await client.get(
        "/api/v1/findings/quality/findings",
        params={"sort": "severity", "order": "desc", "pageSize": 10},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_quality_organization_isolation(client: AsyncClient):
    await _seed_quality_workspace(client)

    await _signup(client, "cq-other@acme.dev", team="Other Org")
    response = await client.get("/api/v1/findings/code-quality/intelligence")
    assert response.status_code == 200
    assert response.json()["hasAnalysisData"] is False
    assert response.json()["totals"]["open"] == 0


@pytest.mark.asyncio
async def test_quality_freshness_running(client: AsyncClient):
    org_id, repo_id = await _seed_quality_workspace(client)
    db = get_database()
    await db.analysis_runs.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "status": "running",
            "trigger": "manual",
            "trigger_source": "manual",
            "created_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
        },
    )

    response = await client.get("/api/v1/findings/quality/intelligence")
    assert response.status_code == 200
    assert response.json()["freshness"]["analysisRunning"] is True
