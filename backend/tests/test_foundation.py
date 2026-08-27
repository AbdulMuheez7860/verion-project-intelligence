import pytest
from httpx import AsyncClient

from app.core.database import get_database
from app.repositories.password_reset_tokens import PasswordResetTokenRepository
from app.repositories.users import UserRepository
from tests.test_auth import _signup


@pytest.mark.asyncio
async def test_ready_endpoint(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["mongodb"]["ok"] is True
    assert body["checks"]["redis"]["ok"] is True


@pytest.mark.asyncio
async def test_paginated_repositories_default_page(client: AsyncClient):
    await _signup(client, "pages@acme.dev")
    response = await client.get("/api/v1/repositories")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert body["page"] == 1
    assert body["total"] == 0
    assert body["hasNext"] is False


@pytest.mark.asyncio
async def test_password_reset_does_not_enumerate_users(client: AsyncClient):
    known = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "missing@acme.dev"},
    )
    assert known.status_code == 204

    await _signup(client, "reset@acme.dev")
    existing = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset@acme.dev"},
    )
    assert existing.status_code == 204


@pytest.mark.asyncio
async def test_password_reset_updates_password(client: AsyncClient):
    await _signup(client, "newpass@acme.dev")
    db = get_database()
    users = UserRepository(db)
    user = await users.get_by_email("newpass@acme.dev")
    assert user is not None

    token_repo = PasswordResetTokenRepository(db)
    raw_token = await token_repo.create(user_id=user["id"], ttl_seconds=3600)

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "password": "new-password-123"},
    )
    assert reset.status_code == 204

    await client.post("/api/v1/auth/logout")
    login_old = await client.post(
        "/api/v1/auth/login",
        json={"email": "newpass@acme.dev", "password": "password123"},
    )
    assert login_old.status_code == 401

    login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": "newpass@acme.dev", "password": "new-password-123"},
    )
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_organization_isolation_for_repository_detail(client: AsyncClient):
    await _signup(client, "orga@acme.dev", team="Org A")
    db = get_database()
    me_a = await client.get("/api/v1/auth/me")
    org_a = me_a.json()["organization"]["id"]

    insert = await db.repositories.insert_one(
        {
            "organization_id": org_a,
            "github_id": 9991,
            "name": "private-repo",
            "owner": "orga",
            "full_name": "orga/private-repo",
            "analysis_status": "not_started",
        },
    )
    repo_id = str(insert.inserted_id)

    await _signup(client, "orgb@acme.dev", team="Org B")
    response = await client.get(f"/api/v1/repositories/{repo_id}")
    assert response.status_code == 404

    await db.repositories.delete_one({"_id": insert.inserted_id})


@pytest.mark.asyncio
async def test_viewer_cannot_connect_repository(client: AsyncClient):
    await _signup(client, "viewer@acme.dev")
    db = get_database()
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]
    await db.memberships.update_one(
        {"user_id": user_id, "organization_id": org_id},
        {"$set": {"role": "viewer"}},
    )

    response = await client.post("/api/v1/repositories", json={"githubId": 123})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_error_response_includes_code(client: AsyncClient):
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "unauthorized"
    assert "requestId" in body


@pytest.mark.asyncio
async def test_production_config_rejects_insecure_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "prod-webhook-secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(ValueError, match="SECRET_KEY"):
        settings.validate_for_startup()
    get_settings.cache_clear()
