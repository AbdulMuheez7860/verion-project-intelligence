import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


async def check_mongodb() -> tuple[bool, str | None]:
    try:
        db = get_database()
        await db.command("ping")
        return True, None
    except Exception as exc:
        logger.warning("MongoDB readiness check failed", exc_info=exc)
        return False, "MongoDB is unavailable."


async def check_redis() -> tuple[bool, str | None]:
    try:
        redis = get_redis()
        await redis.ping()
        return True, None
    except Exception as exc:
        logger.warning("Redis readiness check failed", exc_info=exc)
        return False, "Redis is unavailable."


async def readiness_report() -> dict[str, object]:
    mongo_ok, mongo_error = await check_mongodb()
    redis_ok, redis_error = await check_redis()
    ready = mongo_ok and redis_ok
    checks = {
        "mongodb": {"ok": mongo_ok, "error": mongo_error},
        "redis": {"ok": redis_ok, "error": redis_error},
    }
    return {"status": "ready" if ready else "not_ready", "checks": checks}
