import pytest
from httpx import AsyncClient

from tests.test_auth import _signup


@pytest.mark.asyncio
async def test_get_organization_overview(client: AsyncClient):
    await _signup(client, "org-overview@acme.dev")
    response = await client.get("/api/v1/organization")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Platform"
    assert body["memberCount"] >= 1


@pytest.mark.asyncio
async def test_admin_can_update_organization(client: AsyncClient):
    await _signup(client, "org-update@acme.dev")
    response = await client.patch("/api/v1/organization", json={"name": "Acme Engineering"})
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Engineering"
    assert response.json()["slug"] == "acme-platform"


@pytest.mark.asyncio
async def test_member_cannot_update_organization(client: AsyncClient):
    await _signup(client, "org-member@acme.dev")
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]
    from app.core.database import get_database

    db = get_database()
    await db.memberships.update_one(
        {"user_id": user_id, "organization_id": org_id},
        {"$set": {"role": "member"}},
    )
    response = await client.patch("/api/v1/organization", json={"name": "Hacked"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_members(client: AsyncClient):
    await _signup(client, "members-list@acme.dev")
    response = await client.get("/api/v1/organization/members")
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_create_and_revoke_invitation(client: AsyncClient):
    await _signup(client, "invite@acme.dev")
    created = await client.post(
        "/api/v1/organization/invitations",
        json={"email": "newuser@acme.dev", "role": "member"},
    )
    assert created.status_code == 201
    assert created.json()["emailDeliveryConfigured"] is False
    invitation_id = created.json()["id"]

    duplicate = await client.post(
        "/api/v1/organization/invitations",
        json={"email": "newuser@acme.dev", "role": "member"},
    )
    assert duplicate.status_code == 409

    revoked = await client.delete(f"/api/v1/organization/invitations/{invitation_id}")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_viewer_cannot_create_invitation(client: AsyncClient):
    await _signup(client, "invite-viewer@acme.dev")
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]
    from app.core.database import get_database

    db = get_database()
    await db.memberships.update_one(
        {"user_id": user_id, "organization_id": org_id},
        {"$set": {"role": "viewer"}},
    )
    response = await client.post(
        "/api/v1/organization/invitations",
        json={"email": "x@acme.dev", "role": "viewer"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_admin_access(client: AsyncClient):
    await _signup(client, "audit-admin@acme.dev")
    await client.patch("/api/v1/organization", json={"name": "Audit Org"})
    logs = await client.get("/api/v1/audit-logs")
    assert logs.status_code == 200


@pytest.mark.asyncio
async def test_audit_log_member_denied(client: AsyncClient):
    await _signup(client, "audit-member@acme.dev")
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]
    org_id = me.json()["organization"]["id"]
    from app.core.database import get_database

    db = get_database()
    await db.memberships.update_one(
        {"user_id": user_id, "organization_id": org_id},
        {"$set": {"role": "member"}},
    )
    response = await client.get("/api/v1/audit-logs")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    await _signup(client, "profile@acme.dev")
    response = await client.patch("/api/v1/auth/me", json={"name": "Updated Name", "timezone": "US/Eastern"})
    assert response.status_code == 200
    assert response.json()["user"]["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    await _signup(client, "password@acme.dev")
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "password123", "newPassword": "newpassword123"},
    )
    assert response.status_code == 204
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "password@acme.dev", "password": "newpassword123"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_analysis_settings_readonly(client: AsyncClient):
    await _signup(client, "analysis-settings@acme.dev")
    response = await client.get("/api/v1/organization/analysis-settings")
    assert response.status_code == 200
    body = response.json()
    assert any(s["name"] == "Ruff" and s["supported"] for s in body["codeQualityScanners"])
    assert any(s["name"] == "npm" and not s["supported"] for s in body["dependencyScanners"])
