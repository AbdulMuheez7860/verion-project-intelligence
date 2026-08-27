"""Backfill analysis_snapshots from completed analysis_runs with health_snapshot.

Usage:
    python -m app.scripts.backfill_analysis_snapshots --dry-run
    python -m app.scripts.backfill_analysis_snapshots
    python -m app.scripts.backfill_analysis_snapshots --organization-id <id>
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.database import close_client, get_database
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.services.analysis_snapshot_service import AnalysisSnapshotService

logger = logging.getLogger(__name__)


async def backfill(
    *,
    dry_run: bool = False,
    organization_id: str | None = None,
    repository_id: str | None = None,
) -> dict[str, int]:
    db = get_database()
    snapshots = AnalysisSnapshotRepository(db)
    service = AnalysisSnapshotService(snapshots)

    query: dict = {"status": "complete", "health_snapshot": {"$ne": None}}
    if organization_id:
        query["organization_id"] = organization_id
    if repository_id:
        query["repository_id"] = repository_id

    created = 0
    skipped = 0
    examined = 0

    cursor = db["analysis_runs"].find(query).sort("completed_at", 1)
    async for run in cursor:
        examined += 1
        run_id = str(run["_id"])
        org_id = str(run.get("organization_id", ""))
        repo_id = str(run.get("repository_id", ""))
        health_snapshot = run.get("health_snapshot")
        if not isinstance(health_snapshot, dict):
            skipped += 1
            continue

        existing = await snapshots.get_by_analysis_run(run_id, org_id)
        if existing:
            skipped += 1
            continue

        if dry_run:
            logger.info("Would create snapshot for analysis_run=%s repo=%s", run_id, repo_id)
            created += 1
            continue

        result = await service.create_from_health_snapshot(
            organization_id=org_id,
            repository_id=repo_id,
            analysis_run_id=run_id,
            commit_sha=run.get("commit_sha"),
            branch=run.get("branch"),
            completed_at=run.get("completed_at"),
            health_snapshot=health_snapshot,
            analyzer_summary=run.get("analyzer_summary"),
        )
        if result:
            created += 1
        else:
            skipped += 1

    await close_client()
    return {"examined": examined, "created": created, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill analysis snapshots from completed runs.")
    parser.add_argument("--dry-run", action="store_true", help="Report actions without writing.")
    parser.add_argument("--organization-id", default=None)
    parser.add_argument("--repository-id", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    stats = asyncio.run(
        backfill(
            dry_run=args.dry_run,
            organization_id=args.organization_id,
            repository_id=args.repository_id,
        ),
    )
    logger.info("Backfill complete: %s", stats)


if __name__ == "__main__":
    main()
