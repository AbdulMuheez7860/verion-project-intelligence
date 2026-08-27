from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class PullRequestRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["pull_requests"]

    async def list_by_organization(self, organization_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        docs, _total = await self.list_by_organization_paginated(
            organization_id,
            skip=0,
            limit=limit,
        )
        return docs

    async def list_by_organization_paginated(
        self,
        organization_id: str,
        *,
        skip: int,
        limit: int,
        q: str | None = None,
        repository_id: str | None = None,
        status: str | None = None,
        risk_level: str | None = None,
        verdict: str | None = None,
        author: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if repository_id:
            query["repository_id"] = repository_id
        if status:
            query["status"] = status
        if risk_level:
            query["risk_level"] = risk_level
        if verdict:
            query["verdict"] = verdict
        if author:
            query["author"] = {"$regex": author, "$options": "i"}
        if q:
            pattern = {"$regex": q, "$options": "i"}
            or_clauses: list[dict[str, Any]] = [
                {"title": pattern},
                {"repository_name": pattern},
                {"author": pattern},
            ]
            if q.isdigit():
                number = int(q)
                or_clauses.append({"number": number})
                or_clauses.append({"github_id": number})
            query["$or"] = or_clauses

        total = await self._collection.count_documents(query)
        sort_field = {
            "risk_score": "risk_score",
            "updated_at": "updated_at",
            "created_at": "created_at",
            "repository_name": "repository_name",
            "number": "number",
        }.get(sort, "updated_at")
        direction = 1 if order == "asc" else -1
        cursor = self._collection.find(query).sort(sort_field, direction).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = doc.get("github_id", 0)
            if "_id" in doc:
                doc.pop("_id")
            results.append(doc)
        return results, total

    async def get_by_github_id(self, github_id: int, organization_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"github_id": github_id, "organization_id": organization_id})
        if not doc:
            return None
        doc["id"] = doc.get("github_id", github_id)
        if "_id" in doc:
            doc.pop("_id")
        return doc

    async def count_open_by_organization(self, organization_id: str) -> int:
        return await self._collection.count_documents(
            {"organization_id": organization_id, "status": "open"},
        )

    async def repository_pr_metrics(
        self,
        organization_id: str,
        repository_id: str,
    ) -> dict[str, Any]:
        query = {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "status": "open",
        }
        open_count = await self._collection.count_documents(query)
        high_risk = await self._collection.count_documents(
            {**query, "risk_level": "high"},
        )
        critical_risk = await self._collection.count_documents(
            {**query, "risk_level": "critical"},
        )
        average = await self.average_risk_score(
            organization_id,
            repository_id=repository_id,
        )
        return {
            "open": open_count,
            "high_risk": high_risk,
            "critical_risk": critical_risk,
            "average_risk_score": average,
        }

    async def count_high_risk_open(self, organization_id: str, *, threshold: int = 50) -> int:
        return await self._collection.count_documents(
            {
                "organization_id": organization_id,
                "status": "open",
                "risk_score": {"$gte": threshold},
            },
        )

    async def list_awaiting_risk(
        self,
        organization_id: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {
                "organization_id": organization_id,
                "status": "open",
                "$or": [{"risk_score": None}, {"risk_score": {"$exists": False}}],
            },
        ).sort("created_at", -1).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = doc.get("github_id", 0)
            if "_id" in doc:
                doc.pop("_id")
            results.append(doc)
        return results

    async def list_recently_scored(
        self,
        organization_id: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {
                "organization_id": organization_id,
                "risk_score": {"$ne": None},
                "risk_scored_at": {"$ne": None},
            },
        ).sort("risk_scored_at", -1).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = doc.get("github_id", 0)
            if "_id" in doc:
                doc.pop("_id")
            results.append(doc)
        return results

    async def list_by_repository_paginated(
        self,
        *,
        repository_id: str,
        organization_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"repository_id": repository_id, "organization_id": organization_id, "status": "open"}
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = doc.get("github_id", 0)
            if "_id" in doc:
                doc.pop("_id")
            results.append(doc)
        return results, total

    async def upsert_from_github(
        self,
        *,
        organization_id: str,
        repository_id: str,
        repository_name: str,
        github_id: int,
        number: int | None = None,
        title: str,
        author: str,
        files_changed: int,
        status: str,
        created_at: datetime,
        description: str | None = None,
        draft: bool = False,
        html_url: str | None = None,
        head_sha: str | None = None,
        base_sha: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        update: dict[str, Any] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "title": title,
            "author": author,
            "files_changed": files_changed,
            "status": status,
            "created_at": created_at,
            "description": description,
            "updated_at": now,
            "draft": draft,
        }
        if number is not None:
            update["number"] = number
        if html_url is not None:
            update["html_url"] = html_url
        if head_sha is not None:
            update["head_sha"] = head_sha
        if base_sha is not None:
            update["base_sha"] = base_sha
        await self._collection.update_one(
            {"github_id": github_id, "organization_id": organization_id},
            {
                "$set": update,
                "$setOnInsert": {
                    "github_id": github_id,
                    "organization_id": organization_id,
                    "issues_count": 0,
                },
            },
            upsert=True,
        )

    async def update_risk_score(
        self,
        *,
        github_id: int,
        organization_id: str,
        risk_score: int,
        risk_score_detail: dict[str, Any],
        issues_count: int,
        files_changed: int,
        additions: int,
        deletions: int,
        coverage_percent: float | None = None,
        changed_files: list[str] | None = None,
        file_details: list[dict[str, Any]] | None = None,
        security_issues_count: int = 0,
        quality_issues_count: int = 0,
        dependency_issues_count: int = 0,
        verdict: str | None = None,
        risk_level: str | None = None,
        head_sha: str | None = None,
        base_sha: str | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "risk_score": risk_score,
            "risk_score_detail": risk_score_detail,
            "issues_count": issues_count,
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions,
            "security_issues_count": security_issues_count,
            "quality_issues_count": quality_issues_count,
            "dependency_issues_count": dependency_issues_count,
            "risk_scored_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        if coverage_percent is not None:
            update["coverage_percent"] = coverage_percent
        if changed_files is not None:
            update["changed_files"] = changed_files
        if file_details is not None:
            update["file_details"] = file_details
        if verdict is not None:
            update["verdict"] = verdict
        if risk_level is not None:
            update["risk_level"] = risk_level
        if head_sha is not None:
            update["head_sha"] = head_sha
        if base_sha is not None:
            update["base_sha"] = base_sha
        await self._collection.update_one(
            {"github_id": github_id, "organization_id": organization_id},
            {"$set": update},
        )

    async def average_risk_score(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
    ) -> float | None:
        query: dict[str, Any] = {
            "organization_id": organization_id,
            "risk_score": {"$ne": None},
        }
        if repository_id:
            query["repository_id"] = repository_id
        pipeline = [
            {"$match": query},
            {"$group": {"_id": None, "average": {"$avg": "$risk_score"}}},
        ]
        async for row in self._collection.aggregate(pipeline):
            average = row.get("average")
            if isinstance(average, (int, float)):
                return float(average)
        return None

    async def list_high_risk_by_organization(
        self,
        organization_id: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {
                "organization_id": organization_id,
                "risk_score": {"$ne": None},
                "status": "open",
            },
        ).sort("risk_score", -1).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = doc.get("github_id", 0)
            if "_id" in doc:
                doc.pop("_id")
            results.append(doc)
        return results
