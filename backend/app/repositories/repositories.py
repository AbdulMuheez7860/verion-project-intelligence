from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

RISK_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class RepositoryRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["repositories"]

    @staticmethod
    def _object_id(repository_id: str) -> ObjectId | None:
        """Safely convert a repository ID to ObjectId."""
        try:
            return ObjectId(repository_id)
        except Exception:
            return None

    @staticmethod
    def _with_id(doc: dict[str, Any] | None) -> dict[str, Any] | None:
        """Convert MongoDB _id into the API-facing string id."""
        if not doc:
            return None

        document = dict(doc)

        object_id = document.pop("_id", None)
        if object_id is not None:
            document["id"] = str(object_id)

        return document

    async def list_by_organization(
        self,
        organization_id: str,
    ) -> list[dict[str, Any]]:
        docs, _total = await self.list_by_organization_paginated(
            organization_id,
            skip=0,
            limit=10_000,
        )
        return docs

    async def list_by_organization_paginated(
        self,
        organization_id: str,
        *,
        skip: int,
        limit: int,
        q: str | None = None,
        analysis_status: str | None = None,
        risk_level: str | None = None,
        security_status: str | None = None,
        sort: str = "name",
        order: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {
            "organization_id": organization_id,
        }

        if analysis_status:
            query["analysis_status"] = analysis_status

        if risk_level:
            query["risk_level"] = risk_level

        if q:
            pattern = {
                "$regex": q,
                "$options": "i",
            }

            query["$or"] = [
                {"name": pattern},
                {"owner": pattern},
                {"full_name": pattern},
            ]

        if security_status:
            if security_status == "unavailable":
                query["$or"] = [
                    {"security_score": None},
                    {"security_score": {"$exists": False}},
                ]

            elif security_status == "good":
                query["security_score"] = {"$gte": 80}

            elif security_status == "warning":
                query["security_score"] = {
                    "$gte": 60,
                    "$lt": 80,
                }

            elif security_status == "poor":
                query["security_score"] = {"$lt": 60}

        total = await self._collection.count_documents(query)

        sort_field = {
            "name": "name",
            "health": "health_score",
            "last_analyzed": "last_analyzed_at",
            "open_pull_requests": "open_pull_requests",
            "security": "security_score",
            "security_findings": "security_finding_count",
            "risk": "risk_rank",
        }.get(sort, "name")

        direction = 1 if order.lower() == "asc" else -1

        cursor = (
            self._collection
            .find(query)
            .sort(sort_field, direction)
            .skip(max(skip, 0))
            .limit(max(limit, 1))
        )

        results: list[dict[str, Any]] = []

        async for doc in cursor:
            converted = self._with_id(doc)
            if converted is not None:
                results.append(converted)

        return results, total

    async def has_active_analysis(
        self,
        repository_id: str,
        organization_id: str,
    ) -> bool:
        object_id = self._object_id(repository_id)

        if object_id is None:
            return False

        doc = await self._collection.find_one(
            {
                "_id": object_id,
                "organization_id": organization_id,
                "analysis_status": {
                    "$in": ["queued", "running"],
                },
            },
            projection={"_id": 1},
        )

        return doc is not None

    async def get_by_id(
        self,
        repository_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        object_id = self._object_id(repository_id)

        if object_id is None:
            return None

        doc = await self._collection.find_one(
            {
                "_id": object_id,
                "organization_id": organization_id,
            },
        )

        return self._with_id(doc)

    async def get_by_github_id(
        self,
        github_id: int,
        organization_id: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {
                "github_id": github_id,
                "organization_id": organization_id,
            },
        )

        return self._with_id(doc)

    async def create(
        self,
        *,
        organization_id: str,
        github_id: int,
        name: str,
        owner: str,
        full_name: str,
        language: str | None,
        default_branch: str | None,
        html_url: str | None,
        private: bool,
        webhook_id: int | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)

        doc = {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "github_id": github_id,
            "name": name,
            "owner": owner,
            "full_name": full_name,
            "language": language,
            "default_branch": default_branch,
            "html_url": html_url,
            "private": private,
            "webhook_id": webhook_id,
            "open_pull_requests": 0,
            "analysis_status": "not_started",
            "risk_rank": 0,
            "created_at": now,
            "updated_at": now,
        }

        await self._collection.insert_one(doc)

        converted = self._with_id(doc)

        if converted is None:
            raise RuntimeError("Failed to create repository.")

        return converted

    async def get_by_full_name(
        self,
        full_name: str,
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"full_name": full_name},
        )

        return self._with_id(doc)

    async def delete(
        self,
        repository_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        object_id = self._object_id(repository_id)

        if object_id is None:
            return None

        doc = await self._collection.find_one_and_delete(
            {
                "_id": object_id,
                "organization_id": organization_id,
            },
        )

        return self._with_id(doc)

    async def count_by_organization(
        self,
        organization_id: str,
    ) -> int:
        return await self._collection.count_documents(
            {
                "organization_id": organization_id,
            },
        )

    async def update_analysis_status(
        self,
        repository_id: str,
        organization_id: str,
        *,
        status: str,
    ) -> dict[str, Any] | None:
        object_id = self._object_id(repository_id)

        if object_id is None:
            return None

        now = datetime.now(UTC)

        update: dict[str, Any] = {
            "analysis_status": status,
            "updated_at": now,
        }

        if status == "queued":
            update["analysis_queued_at"] = now

        if status == "complete":
            update["last_analyzed_at"] = now

        result = await self._collection.find_one_and_update(
            {
                "_id": object_id,
                "organization_id": organization_id,
            },
            {
                "$set": update,
            },
            return_document=True,
        )

        return self._with_id(result)

    async def update_from_github(
        self,
        repository_id: str,
        organization_id: str,
        *,
        language: str | None = None,
        open_pull_requests: int | None = None,
        default_branch: str | None = None,
    ) -> dict[str, Any] | None:
        object_id = self._object_id(repository_id)

        if object_id is None:
            return None

        update: dict[str, Any] = {
            "updated_at": datetime.now(UTC),
        }

        if language is not None:
            update["language"] = language

        if open_pull_requests is not None:
            update["open_pull_requests"] = open_pull_requests

        if default_branch is not None:
            update["default_branch"] = default_branch

        result = await self._collection.find_one_and_update(
            {
                "_id": object_id,
                "organization_id": organization_id,
            },
            {
                "$set": update,
            },
            return_document=True,
        )

        return self._with_id(result)

    async def update_scores(
        self,
        repository_id: str,
        organization_id: str,
        *,
        health_score: float,
        security_score: float,
        code_quality_score: float,
        risk_level: str,
        dependency_score: float | None = None,
        dependency_status: str | None = None,
        security_finding_count: int | None = None,
        quality_finding_count: int | None = None,
    ) -> dict[str, Any] | None:
        object_id = self._object_id(repository_id)

        if object_id is None:
            return None

        update: dict[str, Any] = {
            "health_score": health_score,
            "security_score": security_score,
            "code_quality_score": code_quality_score,
            "risk_level": risk_level,
            "risk_rank": RISK_RANK.get(risk_level.lower(), 0),
            "updated_at": datetime.now(UTC),
        }

        if dependency_score is not None:
            update["dependency_score"] = dependency_score

        if dependency_status is not None:
            update["dependency_status"] = dependency_status

        if security_finding_count is not None:
            update["security_finding_count"] = security_finding_count

        if quality_finding_count is not None:
            update["quality_finding_count"] = quality_finding_count

        result = await self._collection.find_one_and_update(
            {
                "_id": object_id,
                "organization_id": organization_id,
            },
            {
                "$set": update,
            },
            return_document=True,
        )

        return self._with_id(result)