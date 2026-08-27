import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_oauth_state_store
from app.core.config import get_settings
from app.core.database import close_client, get_database
from app.core.redis import close_redis
from app.main import create_app

_COLLECTIONS = (
    "users",
    "organizations",
    "memberships",
    "integrations",
    "repositories",
    "pull_requests",
    "webhook_deliveries",
    "password_reset_tokens",
    "findings",
    "analysis_runs",
    "analysis_snapshots",
    "dependencies",
    "invitations",
    "audit_logs",
    "notifications",
    "notification_preferences",
)


class FakeOAuthStateStore:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, str]] = {}
        self._counter = 0

    async def create(self, organization_id: str, *, actor_user_id: str | None = None) -> str:
        self._counter += 1
        state = f"test-state-{self._counter}"
        payload: dict[str, str] = {"organization_id": organization_id}
        if actor_user_id:
            payload["actor_user_id"] = actor_user_id
        self._states[state] = payload
        return state

    async def consume(self, state: str) -> dict[str, str] | None:
        return self._states.pop(state, None)


@pytest_asyncio.fixture
async def client():
    await close_client()
    await close_redis()
    get_settings.cache_clear()

    app = create_app()
    oauth_store = FakeOAuthStateStore()
    app.dependency_overrides[get_oauth_state_store] = lambda: oauth_store
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/health")
        db = get_database()
        for collection in _COLLECTIONS:
            await db[collection].delete_many({})
        yield ac

    await close_client()
    await close_redis()


async def signup_and_login(client: AsyncClient, email: str = "demo@verion.dev") -> None:
    payload = {
        "name": "Demo User",
        "email": email,
        "team": "Acme Platform",
        "password": "password123",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
