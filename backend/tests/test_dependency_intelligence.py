import pytest
from httpx import AsyncClient

from app.core.database import get_database
from tests.test_auth import _signup


async def _seed_dependency_workspace(client: AsyncClient) -> tuple[str, str]:
    await _signup(client, "dep-intel@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "github_id": 77001,
            "name": "api",
            "owner": "acme",
            "full_name": "acme/api",
            "analysis_status": "complete",
            "health_score": 70.0,
            "dependency_score": 60.0,
            "risk_level": "high",
            "last_analyzed_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
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
            "completed_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
            "created_at": __import__("datetime").datetime(2026, 2, 3, 11, 0, 0),
            "finding_count": 2,
            "analyzer_summary": {"executed": ["pip-audit", "semgrep"]},
        },
    )
    await db.dependencies.insert_many(
        [
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-d1",
                "package_name": "requests",
                "current_version": "2.28.0",
                "latest_version": "2.28.0",
                "status": "vulnerable",
                "vulnerability": "PYSEC-2023-1",
                "license": "unknown",
                "created_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
            },
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-d1",
                "package_name": "urllib3",
                "current_version": "1.26.0",
                "latest_version": "1.26.0",
                "status": "healthy",
                "vulnerability": None,
                "license": "unknown",
                "created_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
            },
        ],
    )
    await db.findings.insert_many(
        [
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-d1",
                "severity": "critical",
                "category": "dependency",
                "rule_id": "PYSEC-2023-1",
                "title": "requests: PYSEC-2023-1",
                "description": "Known vulnerability in requests",
                "file": "requirements.txt",
                "line": 1,
                "confidence": 1.0,
                "status": "open",
                "metadata": {"engine": "pip-audit", "package": "requests", "cve": "PYSEC-2023-1"},
                "created_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
            },
            {
                "organization_id": org_id,
                "repository_id": repo_id,
                "analysis_id": "run-d1",
                "severity": "medium",
                "category": "dependency",
                "rule_id": "PYSEC-2022-9",
                "title": "requests: PYSEC-2022-9",
                "description": "Additional vulnerability in requests",
                "file": "requirements.txt",
                "line": 1,
                "confidence": 1.0,
                "status": "open",
                "metadata": {"engine": "pip-audit", "package": "requests", "cve": "PYSEC-2022-9"},
                "created_at": __import__("datetime").datetime(2026, 2, 3, 12, 0, 0),
            },
        ],
    )
    return org_id, repo_id


@pytest.mark.asyncio
async def test_dependency_intelligence_payload(client: AsyncClient):
    await _seed_dependency_workspace(client)

    response = await client.get("/api/v1/findings/dependencies/intelligence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["hasAnalysisData"] is True
    assert payload["posture"]["label"] == "CRITICAL EXPOSURE"
    assert payload["totals"]["total"] == 2
    assert payload["totals"]["vulnerable"] == 1
    assert payload["severityCounts"]["critical"] == 1
    assert payload["scannerCoverage"]["supported"] == ["pip-audit"]
    assert payload["scannerCoverage"]["executed"] == ["pip-audit"]
    assert any(eco["key"] == "python" and eco["supported"] is True for eco in payload["scannerCoverage"]["ecosystems"])
    assert any(eco["key"] == "npm" and eco["supported"] is False for eco in payload["scannerCoverage"]["ecosystems"])
    assert payload["repositories"][0]["vulnerableCount"] == 1
    assert payload["freshness"]["lastAnalyzedAt"] is not None


@pytest.mark.asyncio
async def test_dependency_intelligence_empty_workspace(client: AsyncClient):
    await _signup(client, "dep-empty@acme.dev")

    response = await client.get("/api/v1/findings/dependencies/intelligence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["hasAnalysisData"] is False
    assert payload["posture"]["label"] == "NOT ASSESSED"
    assert payload["totals"]["total"] == 0


@pytest.mark.asyncio
async def test_dependency_list_filters_and_pagination(client: AsyncClient):
    org_id, repo_id = await _seed_dependency_workspace(client)
    db = get_database()
    dep = await db.dependencies.find_one({"organization_id": org_id, "package_name": "requests"})
    dep_id = str(dep["_id"])

    all_deps = await client.get("/api/v1/findings/dependencies?page=1&pageSize=20")
    assert all_deps.status_code == 200
    assert all_deps.json()["total"] == 2

    search = await client.get("/api/v1/findings/dependencies?q=requests")
    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["packageName"] == "requests"
    assert search.json()["items"][0]["severity"] == "critical"

    repo_filter = await client.get(f"/api/v1/findings/dependencies?repositoryId={repo_id}")
    assert repo_filter.status_code == 200
    assert repo_filter.json()["total"] == 2

    severity_filter = await client.get("/api/v1/findings/dependencies?severity=critical")
    assert severity_filter.status_code == 200
    assert severity_filter.json()["total"] == 1

    status_filter = await client.get("/api/v1/findings/dependencies?status=vulnerable")
    assert status_filter.status_code == 200
    assert status_filter.json()["total"] == 1

    ecosystem_filter = await client.get("/api/v1/findings/dependencies?ecosystem=python")
    assert ecosystem_filter.status_code == 200
    assert ecosystem_filter.json()["total"] == 2

    unsupported_ecosystem = await client.get("/api/v1/findings/dependencies?ecosystem=npm")
    assert unsupported_ecosystem.status_code == 422

    sorted_deps = await client.get("/api/v1/findings/dependencies?sort=package_name&order=asc")
    assert sorted_deps.status_code == 200
    names = [item["packageName"] for item in sorted_deps.json()["items"]]
    assert names == sorted(names)

    detail = await client.get(f"/api/v1/findings/dependencies/{dep_id}")
    assert detail.status_code == 200
    assert detail.json()["packageName"] == "requests"


@pytest.mark.asyncio
async def test_dependency_organization_isolation(client: AsyncClient):
    await _seed_dependency_workspace(client)
    await _signup(client, "dep-other@acme.dev", team="Other Org")

    response = await client.get("/api/v1/findings/dependencies")
    assert response.status_code == 200
    assert response.json()["total"] == 0
