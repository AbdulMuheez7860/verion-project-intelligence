import json
import secrets
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings

OAUTH_STATE_TTL_SECONDS = 600


class OAuthStateStore:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    @staticmethod
    def _key(state: str) -> str:
        return f"github:oauth:state:{state}"

    async def create(self, organization_id: str, *, actor_user_id: str | None = None) -> str:
        state = secrets.token_urlsafe(32)
        payload: dict[str, str] = {"organization_id": organization_id}
        if actor_user_id:
            payload["actor_user_id"] = actor_user_id
        await self._client.setex(
            self._key(state),
            OAUTH_STATE_TTL_SECONDS,
            json.dumps(payload),
        )
        return state

    async def consume(self, state: str) -> dict[str, str] | None:
        key = self._key(state)
        raw = await self._client.get(key)
        if not raw:
            return None
        await self._client.delete(key)
        payload = json.loads(raw)
        organization_id = payload.get("organization_id")
        if not isinstance(organization_id, str):
            return None
        result: dict[str, str] = {"organization_id": organization_id}
        actor_user_id = payload.get("actor_user_id")
        if isinstance(actor_user_id, str):
            result["actor_user_id"] = actor_user_id
        return result


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None