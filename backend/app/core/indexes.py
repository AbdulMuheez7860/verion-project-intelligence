"""MongoDB index definitions for application startup.

Webhook delivery idempotency stores GitHub's ``X-GitHub-Delivery`` value as the
document ``_id``. MongoDB always enforces uniqueness on ``_id`` via the default
``_id_`` index — do not create an explicit ``_id`` index.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["users"].create_index("email", unique=True)
    await db["organizations"].create_index("slug", unique=True)
    await db["memberships"].create_index([("user_id", 1), ("organization_id", 1)], unique=True)
    await db["integrations"].create_index([("organization_id", 1), ("provider", 1)], unique=True)
    await db["repositories"].create_index([("organization_id", 1), ("name", 1)])
    await db["repositories"].create_index([("organization_id", 1), ("github_id", 1)], unique=True)
    await db["repositories"].create_index("full_name")
    await db["pull_requests"].create_index([("organization_id", 1), ("github_id", 1)], unique=True)
    await db["pull_requests"].create_index([("organization_id", 1), ("updated_at", -1)])
    await db["pull_requests"].create_index([("organization_id", 1), ("risk_score", -1)])
    await db["pull_requests"].create_index([("organization_id", 1), ("verdict", 1)])
    await db["pull_requests"].create_index([("organization_id", 1), ("repository_id", 1)])
    # webhook_deliveries: _id is the GitHub delivery UUID; uniqueness is automatic.
    await db["findings"].create_index([("organization_id", 1), ("repository_id", 1)])
    await db["findings"].create_index([("organization_id", 1), ("category", 1), ("severity", 1)])
    await db["findings"].create_index([("organization_id", 1), ("category", 1), ("status", 1)])
    await db["findings"].create_index([("organization_id", 1), ("created_at", -1)])
    await db["findings"].create_index([("organization_id", 1), ("category", 1), ("rule_id", 1)])
    await db["analysis_runs"].create_index(
        [("organization_id", 1), ("repository_id", 1), ("created_at", -1)],
    )
    await db["analysis_runs"].create_index([("organization_id", 1), ("started_at", -1)])
    await db["analysis_runs"].create_index(
        [("organization_id", 1), ("repository_id", 1), ("started_at", -1)],
    )
    await db["analysis_runs"].create_index([("organization_id", 1), ("status", 1), ("started_at", -1)])
    await db["analysis_runs"].create_index([("organization_id", 1), ("trigger", 1), ("started_at", -1)])
    await db["dependencies"].create_index([("organization_id", 1), ("repository_id", 1)])
    await db["dependencies"].create_index([("organization_id", 1), ("status", 1)])
    await db["dependencies"].create_index([("organization_id", 1), ("package_name", 1)])
    await db["dependencies"].create_index([("organization_id", 1), ("created_at", -1)])
    # analysis_snapshots: immutable historical points per completed analysis run
    await db["analysis_snapshots"].create_index("analysis_run_id", unique=True)
    await db["analysis_snapshots"].create_index(
        [("organization_id", 1), ("repository_id", 1), ("captured_at", -1)],
    )
    await db["analysis_snapshots"].create_index([("organization_id", 1), ("captured_at", -1)])
    await db["analysis_snapshots"].create_index([("repository_id", 1), ("captured_at", -1)])
    await db["memberships"].create_index([("organization_id", 1), ("created_at", 1)])
    await db["invitations"].create_index([("organization_id", 1), ("status", 1), ("created_at", -1)])
    await db["invitations"].create_index([("organization_id", 1), ("email", 1), ("status", 1)])
    await db["audit_logs"].create_index([("organization_id", 1), ("created_at", -1)])
    await db["audit_logs"].create_index([("organization_id", 1), ("action", 1), ("created_at", -1)])
    await db["audit_logs"].create_index([("organization_id", 1), ("actor_user_id", 1), ("created_at", -1)])
    await db["password_reset_tokens"].create_index("expires_at", expireAfterSeconds=0)
    await db["notifications"].create_index(
        [("organization_id", 1), ("user_id", 1), ("created_at", -1)],
    )
    await db["notifications"].create_index(
        [("organization_id", 1), ("user_id", 1), ("read_at", 1), ("created_at", -1)],
    )
    await db["notifications"].create_index(
        [("user_id", 1), ("idempotency_key", 1)],
        unique=True,
    )
    await db["notification_preferences"].create_index(
        [("organization_id", 1), ("user_id", 1)],
        unique=True,
    )
