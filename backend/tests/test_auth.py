import pytest
from httpx import AsyncClient


async def _signup(client: AsyncClient, email: str, *, team: str = "Acme Platform") -> dict:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Alex Morgan",
            "email": email,
            "team": team,
            "password": "password123",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_signup_creates_user_organization_and_membership(client: AsyncClient):
    body = await _signup(client, "alex@acme.dev")

    assert body["user"]["email"] == "alex@acme.dev"
    assert body["user"]["name"] == "Alex Morgan"
    assert body["organization"]["name"] == "Acme Platform"
    assert body["membership"]["role"] == "owner"
    assert body["membership"]["organizationId"] == body["organization"]["id"]


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(client: AsyncClient):
    await _signup(client, "dup@acme.dev")

    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Another User",
            "email": "dup@acme.dev",
            "team": "Other Team",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert response.json()["message"] == "An account with this email already exists."


@pytest.mark.asyncio
async def test_signup_allows_duplicate_team_names(client: AsyncClient):
    await _signup(client, "team-a@acme.dev", team="Shared Workspace")
    await client.post("/api/v1/auth/logout")
    body = await _signup(client, "team-b@acme.dev", team="Shared Workspace")
    assert body["organization"]["name"] == "Shared Workspace"


@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient):
    await _signup(client, "login@acme.dev")

    await client.post("/api/v1/auth/logout")

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@acme.dev", "password": "password123"},
    )
    assert login.status_code == 200
    login_body = login.json()
    assert login_body["user"]["email"] == "login@acme.dev"
    assert login_body["membership"]["role"] == "owner"

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "login@acme.dev"
    assert me.json()["organization"]["name"] == "Acme Platform"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    await _signup(client, "badlogin@acme.dev")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "badlogin@acme.dev", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_refresh_issues_new_session(client: AsyncClient):
    await _signup(client, "refresh@acme.dev")

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    body = refresh.json()
    assert body["user"]["email"] == "refresh@acme.dev"
    assert body["membership"]["role"] == "owner"

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_refresh_requires_cookie(client: AsyncClient):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["message"] == "Not authenticated."


@pytest.mark.asyncio
async def test_logout_clears_session(client: AsyncClient):
    await _signup(client, "logout@acme.dev")

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_protected_dashboard_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json()["message"] == "Not authenticated."


@pytest.mark.asyncio
async def test_dashboard_empty_state_for_authenticated_user(client: AsyncClient):
    await _signup(client, "dash@acme.dev")

    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["hasAnalysisData"] is False
    assert data["metrics"]["connectedRepositories"] == 0
    assert data["attentionItems"] == []
    assert data["recentPullRequests"] == []


@pytest.mark.asyncio
async def test_security_summary_honest_empty(client: AsyncClient):
    await _signup(client, "sec@acme.dev")

    response = await client.get("/api/v1/findings/security/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["hasAnalysisData"] is False
    assert data.get("score") is None
