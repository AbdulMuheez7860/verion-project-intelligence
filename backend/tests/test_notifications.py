import pytest
from httpx import AsyncClient
from datetime import UTC, datetime

from app.core.database import get_database
from app.repositories.notification_preferences import NotificationPreferencesRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.memberships import MembershipRepository
from app.repositories.pull_requests import PullRequestRepository
from app.services.notification_events import NotificationEventService
from tests.test_auth import _signup


@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient):
    await _signup(client, "notify-empty@acme.dev")
    response = await client.get("/api/v1/notifications")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_unread_count_zero(client: AsyncClient):
    await _signup(client, "notify-unread@acme.dev")
    response = await client.get("/api/v1/notifications/unread-count")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.asyncio
async def test_create_and_list_notification(client: AsyncClient):
    await _signup(client, "notify-create@acme.dev")
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]

    db = get_database()
    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    created = await events.emit(
        organization_id=org_id,
        notification_type="analysis.completed",
        severity="info",
        title="Analysis completed",
        body="payment-service analysis finished with 3 findings.",
        href="/app/analysis-runs/run-1",
        idempotency_key="analysis.completed:run-1",
        repository_id="repo-1",
        repository_name="payment-service",
        resource_type="analysis_run",
        resource_id="run-1",
    )
    assert created == 1

    listed = await client.get("/api/v1/notifications")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Analysis completed"
    assert items[0]["read"] is False
    assert items[0]["repositoryName"] == "payment-service"

    unread = await client.get("/api/v1/notifications/unread-count")
    assert unread.json()["count"] == 1

    notification_id = items[0]["id"]
    marked = await client.patch(f"/api/v1/notifications/{notification_id}/read")
    assert marked.status_code == 200
    assert marked.json()["read"] is True

    unread_after = await client.get("/api/v1/notifications/unread-count")
    assert unread_after.json()["count"] == 0


@pytest.mark.asyncio
async def test_notification_deduplication(client: AsyncClient):
    await _signup(client, "notify-dedup@acme.dev")
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    db = get_database()
    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    first = await events.emit_analysis_completed(
        organization_id=org_id,
        repository_id="repo-1",
        repository_name="api-gateway",
        analysis_run_id="run-dedup",
        finding_count=2,
    )
    second = await events.emit_analysis_completed(
        organization_id=org_id,
        repository_id="repo-1",
        repository_name="api-gateway",
        analysis_run_id="run-dedup",
        finding_count=2,
    )
    assert first == 1
    assert second == 0

    listed = await client.get("/api/v1/notifications")
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient):
    await _signup(client, "notify-markall@acme.dev")
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    db = get_database()
    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    await events.emit_analysis_failed(
        organization_id=org_id,
        repository_id="repo-1",
        repository_name="billing",
        analysis_run_id="run-fail-1",
        error="Clone failed",
    )
    await events.emit_analysis_completed(
        organization_id=org_id,
        repository_id="repo-2",
        repository_name="auth",
        analysis_run_id="run-ok-1",
        finding_count=0,
    )

    response = await client.post("/api/v1/notifications/mark-all-read")
    assert response.status_code == 200
    assert response.json()["updated"] == 2
    assert (await client.get("/api/v1/notifications/unread-count")).json()["count"] == 0


@pytest.mark.asyncio
async def test_notification_preferences(client: AsyncClient):
    await _signup(client, "notify-prefs@acme.dev")
    defaults = await client.get("/api/v1/notification-preferences")
    assert defaults.status_code == 200
    assert defaults.json()["securityAlerts"] is True

    updated = await client.put(
        "/api/v1/notification-preferences",
        json={"securityAlerts": False, "analysisAlerts": True},
    )
    assert updated.status_code == 200
    assert updated.json()["securityAlerts"] is False


@pytest.mark.asyncio
async def test_preferences_filter_security_notifications(client: AsyncClient):
    await _signup(client, "notify-filter@acme.dev")
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    await client.put("/api/v1/notification-preferences", json={"securityAlerts": False})

    db = get_database()
    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    created = await events.emit_critical_security(
        organization_id=org_id,
        repository_id="repo-1",
        repository_name="payments",
        critical_count=2,
        analysis_run_id="run-sec",
    )
    assert created == 0

    listed = await client.get("/api/v1/notifications")
    assert listed.json()["total"] == 0


@pytest.mark.asyncio
async def test_user_isolation(client: AsyncClient):
    await _signup(client, "notify-user-a@acme.dev")
    me_a = await client.get("/api/v1/auth/me")
    org_a = me_a.json()["organization"]["id"]

    db = get_database()
    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    await events.emit_analysis_completed(
        organization_id=org_a,
        repository_id="repo-a",
        repository_name="service-a",
        analysis_run_id="run-a",
        finding_count=1,
    )

    await _signup(client, "notify-user-b@acme.dev", team="Beta Platform")
    listed_b = await client.get("/api/v1/notifications")
    assert listed_b.json()["total"] == 0


@pytest.mark.asyncio
async def test_organization_isolation(client: AsyncClient):
    await _signup(client, "notify-org-a@acme.dev")
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]

    db = get_database()
    await db.notifications.insert_one(
        {
            "organization_id": "other-org",
            "user_id": user_id,
            "type": "analysis.completed",
            "severity": "info",
            "title": "Foreign",
            "body": "Should not appear",
            "href": "/app/analysis-runs/x",
            "idempotency_key": f"foreign:{user_id}",
            "read_at": None,
            "created_at": datetime.now(UTC),
        },
    )

    listed = await client.get("/api/v1/notifications")
    assert all(item["title"] != "Foreign" for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_critical_security_event_content(client: AsyncClient):
    await _signup(client, "notify-security@acme.dev")
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    db = get_database()
    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    await events.emit_critical_security(
        organization_id=org_id,
        repository_id="repo-1",
        repository_name="payment-service",
        critical_count=2,
        analysis_run_id="run-sec-1",
    )

    item = (await client.get("/api/v1/notifications")).json()["items"][0]
    assert item["type"] == "security.critical_finding"
    assert item["severity"] == "critical"
    assert "payment-service" in item["body"]
    assert item["href"] == "/app/security"


@pytest.mark.asyncio
async def test_high_risk_pr_event(client: AsyncClient):
    await _signup(client, "notify-pr@acme.dev")
    me = await client.get("/api/v1/auth/me")
    org_id = me.json()["organization"]["id"]

    db = get_database()
    repo = await db.repositories.insert_one(
        {
            "organization_id": org_id,
            "name": "api",
            "full_name": "acme/api",
            "github_id": 101,
        },
    )
    repo_id = str(repo.inserted_id)
    await db.pull_requests.insert_one(
        {
            "organization_id": org_id,
            "repository_id": repo_id,
            "github_id": 555,
            "number": 42,
            "title": "Refactor auth",
            "status": "open",
            "risk_score": 72,
        },
    )

    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
        PullRequestRepository(db),
    )
    await events.emit_high_risk_prs(
        organization_id=org_id,
        repository_id=repo_id,
        repository_name="acme/api",
        analysis_run_id="run-pr",
    )

    items = (await client.get("/api/v1/notifications")).json()["items"]
    assert any(item["type"] == "pr.high_risk" for item in items)


@pytest.mark.asyncio
async def test_workspace_event_admin_only(client: AsyncClient):
    await _signup(client, "notify-workspace@acme.dev")
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]

    db = get_database()
    member_user = await db.users.insert_one(
        {"email": "member@acme.dev", "name": "Member", "password_hash": "x", "organization_id": org_id},
    )
    member_id = str(member_user.inserted_id)
    await db.memberships.insert_one(
        {"user_id": member_id, "organization_id": org_id, "role": "member"},
    )

    events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
    )
    await events.emit_workspace_event(
        organization_id=org_id,
        notification_type="workspace.member_invited",
        title="Member invited",
        body="Invitation sent to new@acme.dev",
        href="/app/settings/members",
        idempotency_key="workspace.member_invited:test",
    )

    admin_count = await db.notifications.count_documents({"user_id": user_id})
    member_count = await db.notifications.count_documents({"user_id": member_id})
    assert admin_count == 1
    assert member_count == 0


@pytest.mark.asyncio
async def test_invitation_creates_admin_notification(client: AsyncClient):
    await _signup(client, "notify-invite@acme.dev")
    created = await client.post(
        "/api/v1/organization/invitations",
        json={"email": "newmember@acme.dev", "role": "member"},
    )
    assert created.status_code == 201
    items = (await client.get("/api/v1/notifications")).json()["items"]
    assert any(item["type"] == "workspace.member_invited" for item in items)
