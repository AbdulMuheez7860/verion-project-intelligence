from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

CANCELLED_ERROR = "Cancelled by user."


class AnalysisRunRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["analysis_runs"]

    async def create(
        self,
        *,
        repository_id: str,
        organization_id: str,
        trigger: str,
        status: str = "queued",
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": ObjectId(),
            "repository_id": repository_id,
            "organization_id": organization_id,
            "status": status,
            "trigger": trigger,
            "trigger_source": trigger,
            "commit_sha": commit_sha,
            "started_at": now if status == "running" else None,
            "completed_at": None,
            "finding_count": 0,
            "error": None,
            "analyzer_summary": None,
            "created_at": now,
        }
        await self._collection.insert_one(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def mark_running(self, analysis_id: str) -> dict[str, Any] | None:
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(analysis_id)},
            {
                "$set": {
                    "status": "running",
                    "started_at": datetime.now(UTC),
                },
            },
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def mark_complete(
        self,
        analysis_id: str,
        *,
        finding_count: int,
        commit_sha: str | None = None,
        analyzer_summary: dict[str, Any] | None = None,
        health_snapshot: dict[str, Any] | None = None,
        branch: str | None = None,
    ) -> dict[str, Any] | None:
        update: dict[str, Any] = {
            "status": "complete",
            "completed_at": datetime.now(UTC),
            "finding_count": finding_count,
        }
        if commit_sha:
            update["commit_sha"] = commit_sha
        if analyzer_summary is not None:
            update["analyzer_summary"] = analyzer_summary
        if health_snapshot is not None:
            update["health_snapshot"] = health_snapshot
        if branch is not None:
            update["branch"] = branch
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(analysis_id)},
            {"$set": update},
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def mark_failed(self, analysis_id: str, *, error: str) -> dict[str, Any] | None:
        safe_error = error[:500]
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(analysis_id)},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                    "error": safe_error,
                },
            },
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def mark_cancelled(self, analysis_id: str, organization_id: str) -> dict[str, Any] | None:
        result = await self._collection.find_one_and_update(
            {
                "_id": ObjectId(analysis_id),
                "organization_id": organization_id,
                "status": "queued",
            },
            {
                "$set": {
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                    "error": CANCELLED_ERROR,
                },
            },
            return_document=True,
        )
        if not result:
            return None
        result["id"] = str(result.pop("_id"))
        return result

    async def has_active_for_repository(self, repository_id: str, organization_id: str) -> bool:
        count = await self._collection.count_documents(
            {
                "repository_id": repository_id,
                "organization_id": organization_id,
                "status": {"$in": ["queued", "running"]},
            },
            limit=1,
        )
        return count > 0

    async def list_for_organization_paginated(
        self,
        organization_id: str,
        *,
        skip: int,
        limit: int,
        repository_id: str | None = None,
        status: str | None = None,
        trigger: str | None = None,
        q: str | None = None,
        repository_ids: list[str] | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        sort: Literal["started", "completed", "duration", "status"] = "started",
        order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": organization_id}

        if repository_id:
            query["repository_id"] = repository_id
        if repository_ids is not None:
            query["repository_id"] = {"$in": repository_ids}
        if status:
            query["status"] = status
        if trigger == "manual":
            query["trigger"] = {"$in": ["manual", "retry", "connect"]}
        elif trigger == "webhook":
            query["trigger"] = {"$regex": r"^webhook"}
        elif trigger == "scheduled":
            query["trigger"] = "scheduled"
        if started_from or started_to:
            date_filter: dict[str, Any] = {}
            if started_from:
                date_filter["$gte"] = started_from
            if started_to:
                date_filter["$lte"] = started_to
            query["started_at"] = date_filter
        if q:
            q = q.strip()
            if len(q) >= 7 and all(c in "0123456789abcdefABCDEF" for c in q):
                query["commit_sha"] = {"$regex": q, "$options": "i"}
            elif repository_ids is None:
                pass

        sort_field_map = {
            "started": "started_at",
            "completed": "completed_at",
            "status": "status",
            "duration": "started_at",
        }
        sort_field = sort_field_map.get(sort, "started_at")
        sort_dir = -1 if order == "desc" else 1

        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total

    async def latest_for_repository(
        self,
        repository_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"repository_id": repository_id, "organization_id": organization_id},
            sort=[("created_at", -1)],
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def latest_completed_for_repository(
        self,
        repository_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {
                "repository_id": repository_id,
                "organization_id": organization_id,
                "status": "complete",
            },
            sort=[("completed_at", -1)],
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def has_completed_for_organization(self, organization_id: str) -> bool:
        count = await self._collection.count_documents(
            {"organization_id": organization_id, "status": "complete"},
            limit=1,
        )
        return count > 0

    async def has_active_for_organization(self, organization_id: str) -> bool:
        count = await self._collection.count_documents(
            {"organization_id": organization_id, "status": {"$in": ["queued", "running"]}},
            limit=1,
        )
        return count > 0

    async def count_completed_by_organization(self, organization_id: str) -> int:
        return await self._collection.count_documents(
            {"organization_id": organization_id, "status": "complete"},
        )

    async def list_recent_by_organization(
        self,
        organization_id: str,
        *,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find({"organization_id": organization_id}).sort(
            "created_at",
            -1,
        ).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def list_failed_recent(
        self,
        organization_id: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {"organization_id": organization_id, "status": "failed"},
        ).sort("created_at", -1).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def list_latest_completed_summaries(
        self,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "status": "complete",
                },
            },
            {"$sort": {"created_at": -1}},
            {
                "$group": {
                    "_id": "$repository_id",
                    "analyzer_summary": {"$first": "$analyzer_summary"},
                    "completed_at": {"$first": "$completed_at"},
                },
            },
        ]
        results: list[dict[str, Any]] = []
        async for row in self._collection.aggregate(pipeline):
            results.append(
                {
                    "repository_id": str(row.get("_id", "")),
                    "analyzer_summary": row.get("analyzer_summary"),
                    "completed_at": row.get("completed_at"),
                },
            )
        return results

    async def latest_completed_at_for_organization(self, organization_id: str) -> Any:
        doc = await self._collection.find_one(
            {"organization_id": organization_id, "status": "complete"},
            sort=[("completed_at", -1)],
            projection={"completed_at": 1},
        )
        if not doc:
            return None
        return doc.get("completed_at")

    async def get_by_id(self, analysis_id: str, organization_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(analysis_id)
        except Exception:
            return None
        doc = await self._collection.find_one(
            {"_id": object_id, "organization_id": organization_id},
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_by_repository_paginated(
        self,
        *,
        repository_id: str,
        organization_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"repository_id": repository_id, "organization_id": organization_id}
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total

    async def list_completed_health_history(
        self,
        repository_id: str,
        organization_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {
                "repository_id": repository_id,
                "organization_id": organization_id,
                "status": "complete",
                "health_snapshot": {"$ne": None},
            },
        ).sort("completed_at", -1).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results
