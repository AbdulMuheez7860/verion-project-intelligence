import pytest
from httpx import AsyncClient

from app.core.database import get_database
from tests.test_auth import _signup


async def _seed_security_workspace(client: AsyncClient) -> tuple[str, str]:
    await _signup(client, "sec-intel@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 99001,
            "name": "api",
            "owner": "acme",
            "full_name": "acme/api",
            "analysis_status": "complete",
            "health_score": 72.0,
            "security_score": 65.0,
            "code_quality_score": 80.0,
            "risk_level": "high",
            "last_analyzed_at": __import__("datetime").datetime(2026, 2, 1, 12, 0, 0),
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
            "completed_at": __import__("datetime").datetime(2026, 2, 1, 12, 0, 0),
            "created_at": __import__("datetime").datetime(2026, 2, 1, 11, 0, 0),
            "finding_count": 3,
            "analyzer_summary": {"executed": ["semgrep", "bandit", "detect-secrets"]},
        },
    )
    await db.findings.insert_many(
        [
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-1",
                "severity": "critical",
                "category": "security",
                "rule_id": "bandit.B101",
                "title": "Unsafe auth middleware",
                "description": "Potential auth bypass",
                "file": "app/auth.py",
                "line": 12,
                "confidence": 0.9,
                "status": "open",
                "metadata": {"engine": "bandit"},
                "created_at": __import__("datetime").datetime(2026, 2, 1, 12, 0, 0),
            },
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-1",
                "severity": "high",
                "category": "secret",
                "rule_id": "detect-secrets.1",
                "title": "Hardcoded API key",
                "description": "REDACTED",
                "file": "app/config.py",
                "line": 4,
                "confidence": 0.8,
                "status": "open",
                "metadata": {"engine": "detect-secrets"},
                "created_at": __import__("datetime").datetime(2026, 2, 1, 12, 0, 0),
            },
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-1",
                "severity": "medium",
                "category": "dependency",
                "rule_id": "pip-audit.CVE-2024-1",
                "title": "Vulnerable dependency",
                "description": "requests has a known vulnerability",
                "file": "requirements.txt",
                "line": 1,
                "confidence": 1.0,
                "status": "open",
                "metadata": {"engine": "pip-audit", "cve": "CVE-2024-1"},
                "created_at": __import__("datetime").datetime(2026, 2, 1, 12, 0, 0),
            },
        ],
    )
    return org_id, repo_id


@pytest.mark.asyncio
async def test_security_intelligence_payload(client: AsyncClient):
    await _seed_security_workspace(client)

    response = await client.get("/api/v1/findings/security/intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["hasAnalysisData"] is True
    assert body["posture"]["label"] == "CRITICAL EXPOSURE"
    assert body["severityCounts"]["critical"] == 1
    assert body["totals"]["open"] == 3
    assert body["totals"]["repositoriesAffected"] == 1
    assert "semgrep" in body["scannerCoverage"]["executed"]
    assert body["categoryCounts"]["secret"] == 1


@pytest.mark.asyncio
async def test_security_findings_pagination_and_filters(client: AsyncClient):
    await _seed_security_workspace(client)

    response = await client.get(
        "/api/v1/findings/security/findings",
        params={"severity": "critical", "page": 1, "pageSize": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Unsafe auth middleware"


@pytest.mark.asyncio
async def test_security_findings_search(client: AsyncClient):
    await _seed_security_workspace(client)

    response = await client.get("/api/v1/findings/security/findings", params={"q": "auth middleware"})
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_security_findings_repository_filter(client: AsyncClient):
    _org_id, repo_id = await _seed_security_workspace(client)

    response = await client.get(
        "/api/v1/findings/security/findings",
        params={"repositoryId": repo_id, "category": "secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "secret"


@pytest.mark.asyncio
async def test_security_findings_sort_by_severity(client: AsyncClient):
    await _seed_security_workspace(client)

    response = await client.get(
        "/api/v1/findings/security/findings",
        params={"sort": "severity", "order": "desc", "pageSize": 10},
    )
    assert response.status_code == 200
    severities = [item["severity"] for item in response.json()["items"]]
    assert severities[0] == "critical"


@pytest.mark.asyncio
async def test_security_organization_isolation(client: AsyncClient):
    await _seed_security_workspace(client)

    await _signup(client, "sec-other@acme.dev", team="Other Org")
    response = await client.get("/api/v1/findings/security/intelligence")
    assert response.status_code == 200
    assert response.json()["hasAnalysisData"] is False
    assert response.json()["totals"]["open"] == 0


@pytest.mark.asyncio
async def test_security_freshness_running(client: AsyncClient):
    org_id, repo_id = await _seed_security_workspace(client)
    db = get_database()
    await db.analysis_runs.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "status": "running",
            "trigger": "manual",
            "trigger_source": "manual",
            "created_at": __import__("datetime").datetime(2026, 2, 2, 12, 0, 0),
        },
    )

    response = await client.get("/api/v1/findings/security/intelligence")
    assert response.status_code == 200
    assert response.json()["freshness"]["analysisRunning"] is True
    assert response.json()["freshness"]["status"] == "running"
