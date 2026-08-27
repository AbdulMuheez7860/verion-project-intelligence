from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError


class AnalysisSnapshotRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["analysis_snapshots"]

    async def create_snapshot(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Insert a snapshot idempotently.

        A snapshot is uniquely identified by:
        organization_id + analysis_run_id.

        Returns the existing snapshot if it already exists.
        """
        existing = await self.get_by_analysis_run(
            payload["analysis_run_id"],
            payload["organization_id"],
        )

        if existing:
            return existing

        now = datetime.now(UTC)

        doc = {
            "_id": ObjectId(),
            **payload,
            "created_at": now,
        }

        if "captured_at" not in doc or doc["captured_at"] is None:
            doc["captured_at"] = now

        try:
            await self._collection.insert_one(doc)
        except DuplicateKeyError:
            return await self.get_by_analysis_run(
                payload["analysis_run_id"],
                payload["organization_id"],
            )

        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_analysis_run(
        self,
        analysis_run_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {
                "analysis_run_id": analysis_run_id,
                "organization_id": organization_id,
            },
        )

        if not doc:
            return None

        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_latest(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {
            "organization_id": organization_id,
        }

        if repository_id:
            query["repository_id"] = repository_id

        doc = await self._collection.find_one(
            query,
            sort=[("captured_at", -1)],
        )

        if not doc:
            return None

        doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_previous_snapshot(
        self,
        organization_id: str,
        *,
        repository_id: str,
        before_captured_at: datetime,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {
                "organization_id": organization_id,
                "repository_id": repository_id,
                "captured_at": {
                    "$lt": before_captured_at,
                },
            },
            sort=[("captured_at", -1)],
        )

        if not doc:
            return None

        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_for_repository(
        self,
        organization_id: str,
        repository_id: str,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        skip: int = 0,
        limit: int = 200,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {
            "organization_id": organization_id,
            "repository_id": repository_id,
        }

        if from_date or to_date:
            captured: dict[str, Any] = {}

            if from_date:
                captured["$gte"] = from_date

            if to_date:
                captured["$lte"] = to_date

            query["captured_at"] = captured

        total = await self._collection.count_documents(query)

        cursor = (
            self._collection.find(query)
            .sort("captured_at", 1)
            .skip(skip)
            .limit(limit)
        )

        results: list[dict[str, Any]] = []

        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results, total

    async def list_for_organization(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        skip: int = 0,
        limit: int = 500,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {
            "organization_id": organization_id,
        }

        if repository_id:
            query["repository_id"] = repository_id

        if from_date or to_date:
            captured: dict[str, Any] = {}

            if from_date:
                captured["$gte"] = from_date

            if to_date:
                captured["$lte"] = to_date

            query["captured_at"] = captured

        total = await self._collection.count_documents(query)

        cursor = (
            self._collection.find(query)
            .sort("captured_at", 1)
            .skip(skip)
            .limit(limit)
        )

        results: list[dict[str, Any]] = []

        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results, total

    async def count_for_repository(
        self,
        organization_id: str,
        repository_id: str,
    ) -> int:
        return await self._collection.count_documents(
            {
                "organization_id": organization_id,
                "repository_id": repository_id,
            },
        )

    async def count_for_organization(
        self,
        organization_id: str,
    ) -> int:
        return await self._collection.count_documents(
            {
                "organization_id": organization_id,
            },
        )

    async def list_latest_per_repository(
        self,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                },
            },
            {
                "$sort": {
                    "captured_at": -1,
                },
            },
            {
                "$group": {
                    "_id": "$repository_id",
                    "doc": {
                        "$first": "$$ROOT",
                    },
                },
            },
        ]

        results: list[dict[str, Any]] = []

        async for row in self._collection.aggregate(pipeline):
            doc = row.get("doc")

            if not doc:
                continue

            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results

    async def get_snapshot_comparison(
        self,
        organization_id: str,
        repository_id: str,
    ) -> tuple[
        dict[str, Any] | None,
        dict[str, Any] | None,
    ]:
        """Return latest and immediately previous snapshots."""
        latest = await self.get_latest(
            organization_id,
            repository_id=repository_id,
        )

        if not latest:
            return None, None

        captured_at = latest.get("captured_at")

        if not isinstance(captured_at, datetime):
            return latest, None

        previous = await self.get_previous_snapshot(
            organization_id,
            repository_id=repository_id,
            before_captured_at=captured_at,
        )

        return latest, previous

    async def baseline_stats(
        self,
        organization_id: str,
    ) -> dict[str, Any]:
        """Return snapshot count and first/last capture timestamps."""
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                },
            },
            {
                "$group": {
                    "_id": None,
                    "count": {
                        "$sum": 1,
                    },
                    "first_captured_at": {
                        "$min": "$captured_at",
                    },
                    "last_captured_at": {
                        "$max": "$captured_at",
                    },
                },
            },
        ]

        async for row in self._collection.aggregate(pipeline):
            return {
                "count": int(row.get("count", 0)),
                "first_captured_at": row.get(
                    "first_captured_at",
                ),
                "last_captured_at": row.get(
                    "last_captured_at",
                ),
            }

        return {
            "count": 0,
            "first_captured_at": None,
            "last_captured_at": None,
        }