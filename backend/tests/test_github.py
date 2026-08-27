import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.test_auth import _signup


def _sign_payload(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def github_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_github_integration_not_configured(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    await _signup(client, "gh@acme.dev")

    response = await client.get("/api/v1/integrations/github")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["status"] == "not_connected"


@pytest.mark.asyncio
async def test_github_connect_requires_configuration(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    await _signup(client, "ghconnect@acme.dev")

    response = await client.post("/api/v1/integrations/github/connect")
    assert response.status_code == 503


@pytest.mark.asyncio
@patch("app.services.github_integration.GitHubClient.get_authenticated_user", new_callable=AsyncMock)
@patch("app.services.github_integration.exchange_oauth_code", new_callable=AsyncMock)
async def test_github_oauth_callback_stores_integration(
    mock_exchange: AsyncMock,
    mock_get_user: AsyncMock,
    client: AsyncClient,
    github_env: None,
):
    await _signup(client, "oauth@acme.dev")

    connect = await client.post("/api/v1/integrations/github/connect")
    assert connect.status_code == 200
    authorize_url = connect.json()["authorizeUrl"]
    state = authorize_url.split("state=")[-1]

    mock_exchange.return_value = {"access_token": "gho_test", "scope": "repo,read:user"}
    mock_get_user.return_value = {"id": 42, "login": "octocat"}

    callback = await client.get(
        f"/api/v1/integrations/github/callback?code=test-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "github=connected" in callback.headers["location"]

    status_response = await client.get("/api/v1/integrations/github")
    assert status_response.status_code == 200


@pytest.mark.asyncio
@patch("app.services.github_integration.GitHubClient.get_authenticated_user", new_callable=AsyncMock)
@patch("app.services.github_integration.exchange_oauth_code", new_callable=AsyncMock)
async def test_oauth_callback_never_logs_the_authorization_code(
    mock_exchange: AsyncMock,
    mock_get_user: AsyncMock,
    client: AsyncClient,
    github_env: None,
    caplog: pytest.LogCaptureFixture,
):
    """
    Regression test: the OAuth authorization `code` and `state` are
    secrets-in-transit and must never appear in application logs.
    `RedactedAccessLogMiddleware` logs `request.url.path` only (never
    `request.url` / the query string), and uvicorn's own access log
    (which does log the full request line) is disabled via
    `--no-access-log` in the Dockerfile - this test only covers the
    application-level logger, since the test client does not go
    through the uvicorn process.
    """

    await _signup(client, "oauth-log@acme.dev")

    connect = await client.post("/api/v1/integrations/github/connect")
    authorize_url = connect.json()["authorizeUrl"]
    state = authorize_url.split("state=")[-1]

    mock_exchange.return_value = {"access_token": "gho_test", "scope": "repo,read:user"}
    mock_get_user.return_value = {"id": 42, "login": "octocat"}

    secret_code = "super-secret-oauth-code-should-never-be-logged"

    with caplog.at_level("INFO", logger="verion.access"):
        await client.get(
            f"/api/v1/integrations/github/callback?code={secret_code}&state={state}",
            follow_redirects=False,
        )

    for record in caplog.records:
        assert secret_code not in record.getMessage()
        assert state not in record.getMessage()
    body = status_response.json()
    assert body["status"] == "connected"
    assert body["githubLogin"] == "octocat"


@pytest.mark.asyncio
@patch("app.workers.tasks.analysis.enqueue_analysis")
@patch("app.integrations.github.client.GitHubClient.create_repository_webhook", new_callable=AsyncMock)
@patch("app.integrations.github.client.GitHubClient.get_repository", new_callable=AsyncMock)
@patch("app.services.github_integration.GitHubClient.list_repositories", new_callable=AsyncMock)
@patch("app.services.github_integration.GitHubClient.get_authenticated_user", new_callable=AsyncMock)
@patch("app.services.github_integration.exchange_oauth_code", new_callable=AsyncMock)
async def test_connect_repository_creates_record(
    mock_exchange: AsyncMock,
    mock_get_user: AsyncMock,
    mock_list_repos: AsyncMock,
    mock_get_repo: AsyncMock,
    mock_create_hook: AsyncMock,
    mock_enqueue: AsyncMock,
    client: AsyncClient,
    github_env: None,
):
    mock_exchange.return_value = {"access_token": "gho_test", "scope": "repo,read:user"}
    mock_get_user.return_value = {"id": 42, "login": "octocat"}
    mock_list_repos.return_value = [
        {
            "id": 123,
            "name": "hello-world",
            "full_name": "octocat/hello-world",
            "owner": {"login": "octocat"},
            "language": "TypeScript",
            "private": False,
            "default_branch": "main",
            "html_url": "https://github.com/octocat/hello-world",
        },
    ]
    mock_get_repo.return_value = {
        "language": "TypeScript",
        "default_branch": "main",
        "html_url": "https://github.com/octocat/hello-world",
        "private": False,
    }
    mock_create_hook.return_value = {"id": 999}

    await _signup(client, "repo@acme.dev")
    connect = await client.post("/api/v1/integrations/github/connect")
    state = connect.json()["authorizeUrl"].split("state=")[-1]
    await client.get(f"/api/v1/integrations/github/callback?code=test-code&state={state}")

    response = await client.post("/api/v1/repositories", json={"githubId": 123})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "hello-world"
    assert body["owner"] == "octocat"
    assert body["githubId"] == 123
    mock_enqueue.assert_called_once()


@pytest.mark.asyncio
@patch("app.workers.tasks.webhooks.process_github_webhook.delay")
async def test_github_webhook_accepts_signed_payload(
    mock_delay: AsyncMock,
    client: AsyncClient,
    github_env: None,
):
    await _signup(client, "hook@acme.dev")

    from app.core.database import get_database

    db = get_database()
    me = await client.get("/api/v1/auth/me")
    organization_id = me.json()["organization"]["id"]
    insert = await db.repositories.insert_one(
        {
            "organization_id": organization_id,
            "github_id": 123,
            "name": "hello-world",
            "owner": "octocat",
            "full_name": "octocat/hello-world",
            "analysis_status": "not_started",
        },
    )

    payload = {"repository": {"full_name": "octocat/hello-world"}}
    raw = json.dumps(payload).encode()
    response = await client.post(
        "/api/v1/webhooks/github",
        content=raw,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-1",
            "X-Hub-Signature-256": _sign_payload(raw, "webhook-secret"),
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    mock_delay.assert_called_once()
    await db.repositories.delete_one({"_id": insert.inserted_id})


@pytest.mark.asyncio
async def test_github_webhook_rejects_invalid_signature(client: AsyncClient, github_env: None):
    payload = json.dumps({"repository": {"full_name": "octocat/hello-world"}}).encode()
    response = await client.post(
        "/api/v1/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-2",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_rejects_missing_signature_when_secret_configured(
    client: AsyncClient,
    github_env: None,
):
    payload = json.dumps({"repository": {"full_name": "octocat/hello-world"}}).encode()
    response = await client.post(
        "/api/v1/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-missing-sig",
        },
    )
    assert response.status_code == 401
