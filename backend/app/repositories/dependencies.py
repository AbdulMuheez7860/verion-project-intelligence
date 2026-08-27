from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analyzers.dependencies import DependencyRecord


class DependencyRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["dependencies"]

    async def replace_for_analysis(
        self,
        *,
        organization_id: str,
        repository_id: str,
        analysis_id: str,
        records: list[DependencyRecord],
    ) -> int:
        await self._collection.delete_many(
            {"organization_id": organization_id, "repository_id": repository_id},
        )
        if not records:
            return 0

        now = datetime.now(UTC)
        docs: list[dict[str, Any]] = []
        for record in records:
            docs.append(
                {
                    "_id": ObjectId(),
                    "organization_id": organization_id,
                    "repository_id": repository_id,
                    "analysis_id": analysis_id,
                    "package_name": record.package_name,
                    "current_version": record.current_version,
                    "latest_version": record.latest_version,
                    "status": record.status,
                    "vulnerability": record.vulnerability,
                    "license": record.license,
                    "created_at": now,
                },
            )
        await self._collection.insert_many(docs)
        return len(docs)

    async def list_by_organization(self, organization_id: str, limit: int = 500) -> list[dict[str, Any]]:
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
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"organization_id": organization_id}
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("package_name", 1).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total

    async def get_by_id(self, dependency_id: str, organization_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(dependency_id)
        except Exception:
            return None
        doc = await self._collection.find_one({"_id": object_id, "organization_id": organization_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_paginated(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
        status: str | None = None,
        q: str | None = None,
        repository_ids_for_search: list[str] | None = None,
        package_keys_for_severity: list[dict[str, str]] | None = None,
        sort: str = "status",
        order: str = "desc",
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if repository_id:
            query["repository_id"] = repository_id
        if status:
            query["status"] = status
        if package_keys_for_severity:
            query["$or"] = [
                {"repository_id": key["repository_id"], "package_name": key["package_name"]}
                for key in package_keys_for_severity
            ]
        if q:
            pattern = {"$regex": q, "$options": "i"}
            or_clauses: list[dict[str, Any]] = [
                {"package_name": pattern},
                {"vulnerability": pattern},
            ]
            if repository_ids_for_search:
                or_clauses.append({"repository_id": {"$in": repository_ids_for_search}})
            if "$or" in query:
                query = {"$and": [query, {"$or": or_clauses}]}
            else:
                query["$or"] = or_clauses

        total = await self._collection.count_documents(query)

        if sort == "status":
            status_direction = 1 if order == "desc" else -1
            pipeline: list[dict[str, Any]] = [
                {"$match": query},
                {
                    "$addFields": {
                        "status_rank": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$status", "critical"]}, "then": 0},
                                    {"case": {"$eq": ["$status", "vulnerable"]}, "then": 1},
                                    {"case": {"$eq": ["$status", "outdated"]}, "then": 2},
                                    {"case": {"$eq": ["$status", "healthy"]}, "then": 3},
                                ],
                                "default": 4,
                            },
                        },
                    },
                },
                {"$sort": {"status_rank": status_direction, "package_name": 1}},
                {"$skip": skip},
                {"$limit": limit},
            ]
            results: list[dict[str, Any]] = []
            async for doc in self._collection.aggregate(pipeline):
                doc["id"] = str(doc.pop("_id"))
                doc.pop("status_rank", None)
                results.append(doc)
            return results, total

        direction = 1 if order == "asc" else -1
        sort_field = {
            "package_name": "package_name",
            "current_version": "current_version",
            "created_at": "created_at",
            "repository_name": "repository_id",
            "severity": "package_name",
        }.get(sort, "package_name")

        if sort == "severity":
            severity_direction = 1 if order == "desc" else -1
            pipeline = [
                {"$match": query},
                {
                    "$lookup": {
                        "from": "findings",
                        "let": {
                            "repo_id": "$repository_id",
                            "pkg": "$package_name",
                            "org_id": "$organization_id",
                        },
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$organization_id", "$$org_id"]},
                                            {"$eq": ["$category", "dependency"]},
                                            {"$eq": ["$repository_id", "$$repo_id"]},
                                            {"$eq": ["$metadata.package", "$$pkg"]},
                                        ],
                                    },
                                },
                            },
                        ],
                        "as": "vuln_findings",
                    },
                },
                {
                    "$addFields": {
                        "severity_rank": {
                            "$cond": [
                                {"$gt": [{"$size": "$vuln_findings"}, 0]},
                                {
                                    "$min": {
                                        "$map": {
                                            "input": "$vuln_findings",
                                            "as": "finding",
                                            "in": {
                                                "$switch": {
                                                    "branches": [
                                                        {
                                                            "case": {"$eq": ["$$finding.severity", "critical"]},
                                                            "then": 0,
                                                        },
                                                        {
                                                            "case": {"$eq": ["$$finding.severity", "high"]},
                                                            "then": 1,
                                                        },
                                                        {
                                                            "case": {"$eq": ["$$finding.severity", "medium"]},
                                                            "then": 2,
                                                        },
                                                        {
                                                            "case": {"$eq": ["$$finding.severity", "low"]},
                                                            "then": 3,
                                                        },
                                                    ],
                                                    "default": 4,
                                                },
                                            },
                                        },
                                    },
                                },
                                5,
                            ],
                        },
                    },
                },
                {"$sort": {"severity_rank": severity_direction, "package_name": 1}},
                {"$skip": skip},
                {"$limit": limit},
            ]
            results = []
            async for doc in self._collection.aggregate(pipeline):
                doc["id"] = str(doc.pop("_id"))
                doc.pop("severity_rank", None)
                doc.pop("vuln_findings", None)
                results.append(doc)
            return results, total

        cursor = self._collection.find(query).sort(sort_field, direction).skip(skip).limit(limit)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total

    async def repository_stats(self, organization_id: str) -> list[dict[str, Any]]:
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {
                "$group": {
                    "_id": "$repository_id",
                    "dependency_count": {"$sum": 1},
                    "vulnerable_count": {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$status", ["vulnerable", "critical"]]},
                                1,
                                0,
                            ],
                        },
                    },
                },
            },
            {"$sort": {"vulnerable_count": -1, "dependency_count": -1}},
        ]
        results: list[dict[str, Any]] = []
        async for row in self._collection.aggregate(pipeline):
            results.append(
                {
                    "repository_id": str(row.get("_id", "")),
                    "dependency_count": int(row.get("dependency_count", 0)),
                    "vulnerable_count": int(row.get("vulnerable_count", 0)),
                },
            )
        return results

    async def top_vulnerable_packages(
        self,
        organization_id: str,
        *,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "status": {"$in": ["vulnerable", "critical"]},
                },
            },
            {
                "$group": {
                    "_id": "$package_name",
                    "count": {"$sum": 1},
                    "vulnerable_count": {"$sum": 1},
                    "repositories": {"$addToSet": "$repository_id"},
                    "vulnerability": {"$first": "$vulnerability"},
                },
            },
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        results: list[dict[str, Any]] = []
        async for row in self._collection.aggregate(pipeline):
            results.append(
                {
                    "package_name": str(row.get("_id", "")),
                    "count": int(row.get("count", 0)),
                    "vulnerable_count": int(row.get("vulnerable_count", 0)),
                    "repository_count": len(row.get("repositories", [])),
                    "vulnerability": row.get("vulnerability"),
                },
            )
        return results

    async def count_repositories_with_vulnerabilities(self, organization_id: str) -> int:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "status": {"$in": ["vulnerable", "critical"]},
                },
            },
            {"$group": {"_id": "$repository_id"}},
            {"$count": "total"},
        ]
        async for row in self._collection.aggregate(pipeline):
            return int(row.get("total", 0))
        return 0

    async def summary_counts(self, organization_id: str) -> dict[str, int]:
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        # BUG FIX: an explicit "unknown" bucket is required alongside
        # the others - without it, dependency records from
        # inventory-only ecosystems (Go/Rust/PHP/Ruby) still count
        # toward `total` but vanish from every named bucket, which
        # made downstream "fall back to healthy when total > 0 and
        # nothing else matched" logic wrongly report them as
        # verified-healthy instead of never-scanned.
        counts = {
            "total": 0,
            "outdated": 0,
            "vulnerable": 0,
            "critical": 0,
            "healthy": 0,
            "unknown": 0,
        }
        async for row in self._collection.aggregate(pipeline):
            status = str(row.get("_id", "healthy"))
            count = int(row.get("count", 0))
            counts["total"] += count
            if status in counts:
                counts[status] = count
        return counts

    async def summary_counts_for_repository(
        self,
        repository_id: str,
        organization_id: str,
    ) -> dict[str, int]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "repository_id": repository_id,
                },
            },
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        counts = {
            "total": 0,
            "outdated": 0,
            "vulnerable": 0,
            "critical": 0,
            "healthy": 0,
            "unknown": 0,
        }
        async for row in self._collection.aggregate(pipeline):
            status = str(row.get("_id", "healthy"))
            count = int(row.get("count", 0))
            counts["total"] += count
            if status in counts:
                counts[status] = count
        return counts

    async def list_by_repository_paginated(
        self,
        repository_id: str,
        organization_id: str,
        *,
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"organization_id": organization_id, "repository_id": repository_id}
        total = await self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("package_name", 1).skip(skip).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results, total
