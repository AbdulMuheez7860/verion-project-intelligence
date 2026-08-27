from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.analyzers.base import AnalyzerFinding
from app.lib.security_helpers import SECURITY_CATEGORIES

QUALITY_CATEGORIES = ("quality",)

SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


class FindingRepository:
    """
    Repository for normalized Verion analyzer findings.

    Design goals:
    - Organization isolation
    - Repository isolation
    - Analysis isolation
    - Stable pagination
    - Correct severity ordering
    - Safe finding replacement
    - Efficient MongoDB queries
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["findings"]

    # ------------------------------------------------------------------
    # INDEXES
    # ------------------------------------------------------------------

    async def ensure_indexes(self) -> None:
        """
        Create indexes required by the findings API and dashboard.

        Safe to call during application startup.
        """
        await self._collection.create_indexes(
            [
                {
                    "name": "organization_repository_created",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("repository_id", ASCENDING),
                        ("created_at", DESCENDING),
                    ],
                },
                {
                    "name": "organization_analysis",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("analysis_id", ASCENDING),
                    ],
                },
                {
                    "name": "organization_category_severity",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("category", ASCENDING),
                        ("severity", ASCENDING),
                    ],
                },
                {
                    "name": "organization_status",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("status", ASCENDING),
                    ],
                },
                {
                    "name": "organization_repository_category",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("repository_id", ASCENDING),
                        ("category", ASCENDING),
                    ],
                },
                {
                    "name": "organization_repository_severity",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("repository_id", ASCENDING),
                        ("severity", ASCENDING),
                    ],
                },
                {
                    "name": "organization_rule",
                    "key": [
                        ("organization_id", ASCENDING),
                        ("rule_id", ASCENDING),
                    ],
                },
            ]
        )

    # ------------------------------------------------------------------
    # INSERT / REPLACEMENT
    # ------------------------------------------------------------------

    async def replace_for_analysis(
        self,
        *,
        organization_id: str,
        repository_id: str,
        analysis_id: str,
        findings: list[AnalyzerFinding],
    ) -> int:
        """
        Replace findings belonging to the supplied analysis.

        We never delete findings belonging to another analysis.
        """
        query = {
            "organization_id": organization_id,
            "repository_id": repository_id,
            "analysis_id": analysis_id,
        }

        await self._collection.delete_many(query)

        if not findings:
            return 0

        now = datetime.now(UTC)

        docs: list[dict[str, Any]] = []

        for finding in findings:
            docs.append(
                {
                    "_id": ObjectId(),
                    "organization_id": organization_id,
                    "repository_id": repository_id,
                    "analysis_id": analysis_id,
                    "severity": finding.severity,
                    "category": finding.category,
                    "rule_id": finding.rule_id,
                    "title": finding.title,
                    "description": finding.description,
                    "file": finding.file,
                    "line": max(1, finding.line),
                    "confidence": max(
                        0.0,
                        min(1.0, finding.confidence),
                    ),
                    "remediation": finding.remediation,
                    "status": "open",
                    "metadata": finding.metadata,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        await self._collection.insert_many(
            docs,
            ordered=False,
        )

        return len(docs)

    # ------------------------------------------------------------------
    # GENERIC ORGANIZATION QUERIES
    # ------------------------------------------------------------------

    async def list_by_organization(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        docs, _total = await self.list_by_organization_paginated(
            organization_id,
            categories=categories,
            skip=0,
            limit=limit,
        )
        return docs

    async def list_by_organization_paginated(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = max(0, skip)
        limit = max(1, min(limit, 500))

        query: dict[str, Any] = {
            "organization_id": organization_id,
        }

        if categories:
            query["category"] = {
                "$in": categories,
            }

        total = await self._collection.count_documents(query)

        pipeline = [
            {
                "$match": query,
            },
            {
                "$addFields": {
                    "severity_rank": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$eq": [
                                            "$severity",
                                            "critical",
                                        ],
                                    },
                                    "then": SEVERITY_RANK["critical"],
                                },
                                {
                                    "case": {
                                        "$eq": [
                                            "$severity",
                                            "high",
                                        ],
                                    },
                                    "then": SEVERITY_RANK["high"],
                                },
                                {
                                    "case": {
                                        "$eq": [
                                            "$severity",
                                            "medium",
                                        ],
                                    },
                                    "then": SEVERITY_RANK["medium"],
                                },
                                {
                                    "case": {
                                        "$eq": [
                                            "$severity",
                                            "low",
                                        ],
                                    },
                                    "then": SEVERITY_RANK["low"],
                                },
                            ],
                            "default": 4,
                        },
                    },
                },
            },
            {
                "$sort": {
                    "severity_rank": ASCENDING,
                    "created_at": DESCENDING,
                    "_id": DESCENDING,
                },
            },
            {
                "$skip": skip,
            },
            {
                "$limit": limit,
            },
        ]

        results: list[dict[str, Any]] = []

        async for doc in self._collection.aggregate(pipeline):
            doc["id"] = str(doc.pop("_id"))
            doc.pop("severity_rank", None)
            results.append(doc)

        return results, total

    # ------------------------------------------------------------------
    # SEVERITY COUNTS
    # ------------------------------------------------------------------

    async def count_by_severity(
        self,
        organization_id: str,
        categories: list[str],
    ) -> dict[str, int]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": {
                        "$in": categories,
                    },
                },
            },
            {
                "$group": {
                    "_id": "$severity",
                    "count": {
                        "$sum": 1,
                    },
                },
            },
        ]

        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        async for row in self._collection.aggregate(pipeline):
            severity = str(row.get("_id", "low"))

            if severity in counts:
                counts[severity] = int(
                    row.get("count", 0)
                )

        return counts

    async def count_by_severity_for_repository(
        self,
        repository_id: str,
        organization_id: str,
        *,
        categories: list[str] | None = None,
    ) -> dict[str, int]:
        match: dict[str, Any] = {
            "organization_id": organization_id,
            "repository_id": repository_id,
        }

        if categories:
            match["category"] = {
                "$in": categories,
            }

        pipeline = [
            {
                "$match": match,
            },
            {
                "$group": {
                    "_id": "$severity",
                    "count": {
                        "$sum": 1,
                    },
                },
            },
        ]

        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        async for row in self._collection.aggregate(pipeline):
            severity = str(row.get("_id", "low"))

            if severity in counts:
                counts[severity] = int(
                    row.get("count", 0)
                )

        return counts

    # ------------------------------------------------------------------
    # ANALYSIS STATISTICS
    # ------------------------------------------------------------------

    async def count_by_category_for_analysis(
        self,
        analysis_id: str,
        organization_id: str,
    ) -> dict[str, int]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "analysis_id": analysis_id,
                },
            },
            {
                "$group": {
                    "_id": "$category",
                    "count": {
                        "$sum": 1,
                    },
                },
            },
        ]

        counts: dict[str, int] = {}

        async for row in self._collection.aggregate(pipeline):
            category = str(row.get("_id", "unknown"))

            counts[category] = int(
                row.get("count", 0)
            )

        return counts

    # ------------------------------------------------------------------
    # REPOSITORY QUERIES
    # ------------------------------------------------------------------

    async def list_by_repository(
        self,
        repository_id: str,
        organization_id: str,
        *,
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {
            "organization_id": organization_id,
            "repository_id": repository_id,
        }

        if categories:
            query["category"] = {
                "$in": categories,
            }

        cursor = (
            self._collection
            .find(query)
            .sort(
                [
                    ("created_at", DESCENDING),
                    ("_id", DESCENDING),
                ]
            )
        )

        results: list[dict[str, Any]] = []

        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results

    async def top_by_severity_for_repository(
        self,
        repository_id: str,
        organization_id: str,
        *,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Return the `limit` highest-severity findings for a repository,
        sorted critical-first, plus the total finding count.

        This exists for consumers (e.g. the AI assistant) that need a
        small, severity-ranked slice of findings rather than the full
        list. Sorting/limiting happens in MongoDB via aggregation
        instead of fetching every finding for the repository and
        sorting it in Python, and only the fields actually used by
        those consumers are projected back, to avoid transferring full
        finding documents (which include verbose metadata) just to
        read a handful of scalar fields.
        """

        limit = max(1, min(limit, 500))

        query: dict[str, Any] = {
            "organization_id": organization_id,
            "repository_id": repository_id,
        }

        total = await self._collection.count_documents(query)

        if total == 0:
            return [], 0

        pipeline: list[dict[str, Any]] = [
            {"$match": query},
            {
                "$addFields": {
                    "severity_rank": {
                        "$switch": {
                            "branches": [
                                {"case": {"$eq": ["$severity", "critical"]}, "then": SEVERITY_RANK["critical"]},
                                {"case": {"$eq": ["$severity", "high"]}, "then": SEVERITY_RANK["high"]},
                                {"case": {"$eq": ["$severity", "medium"]}, "then": SEVERITY_RANK["medium"]},
                                {"case": {"$eq": ["$severity", "low"]}, "then": SEVERITY_RANK["low"]},
                            ],
                            "default": 99,
                        },
                    },
                },
            },
            {"$sort": {"severity_rank": ASCENDING, "created_at": DESCENDING, "_id": DESCENDING}},
            {"$limit": limit},
            {
                "$project": {
                    "category": 1,
                    "severity": 1,
                    "status": 1,
                    "rule_id": 1,
                    "title": 1,
                    "description": 1,
                    "file": 1,
                    "line": 1,
                    "remediation": 1,
                    "metadata": 1,
                },
            },
        ]

        results: list[dict[str, Any]] = []

        async for doc in self._collection.aggregate(pipeline):
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results, total

    async def list_by_repository_paginated(
        self,
        repository_id: str,
        organization_id: str,
        *,
        categories: list[str] | None = None,
        severity: str | None = None,
        status: str | None = None,
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = max(0, skip)
        limit = max(1, min(limit, 500))

        query: dict[str, Any] = {
            "organization_id": organization_id,
            "repository_id": repository_id,
        }

        if categories:
            query["category"] = {
                "$in": categories,
            }

        if severity:
            query["severity"] = severity

        if status:
            query["status"] = status

        total = await self._collection.count_documents(query)

        cursor = (
            self._collection
            .find(query)
            .sort(
                [
                    ("created_at", DESCENDING),
                    ("_id", DESCENDING),
                ]
            )
            .skip(skip)
            .limit(limit)
        )

        results: list[dict[str, Any]] = []

        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results, total

    # ------------------------------------------------------------------
    # SECURITY FINDINGS
    # ------------------------------------------------------------------

    async def list_security_paginated(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
        repository_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        rule_id: str | None = None,
        q: str | None = None,
        repository_ids_for_search: list[str] | None = None,
        sort: str = "severity",
        order: str = "desc",
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = max(0, skip)
        limit = max(1, min(limit, 500))

        active_categories = list(
            categories or SECURITY_CATEGORIES
        )

        query: dict[str, Any] = {
            "organization_id": organization_id,
            "category": {
                "$in": active_categories,
            },
        }

        if repository_id:
            query["repository_id"] = repository_id

        if severity:
            query["severity"] = severity

        if status:
            query["status"] = status

        if rule_id:
            query["rule_id"] = rule_id

        if q:
            import re

            search_text = q.strip()

            if search_text:
                escaped_q = re.escape(search_text)

                pattern = {
                    "$regex": escaped_q,
                    "$options": "i",
                }

                or_clauses: list[dict[str, Any]] = [
                    {"title": pattern},
                    {"file": pattern},
                    {"rule_id": pattern},
                    {"description": pattern},
                ]

                if repository_ids_for_search:
                    or_clauses.append(
                        {
                            "repository_id": {
                                "$in": repository_ids_for_search,
                            }
                        }
                    )

                query["$or"] = or_clauses

        total = await self._collection.count_documents(query)

        # --------------------------------------------------------------
        # SEVERITY SORT
        # --------------------------------------------------------------

        if sort == "severity":
            rank_direction = (
                ASCENDING
                if order == "desc"
                else DESCENDING
            )

            pipeline: list[dict[str, Any]] = [
                {
                    "$match": query,
                },
                {
                    "$addFields": {
                        "severity_rank": {
                            "$switch": {
                                "branches": [
                                    {
                                        "case": {
                                            "$eq": [
                                                "$severity",
                                                "critical",
                                            ],
                                        },
                                        "then": SEVERITY_RANK["critical"],
                                    },
                                    {
                                        "case": {
                                            "$eq": [
                                                "$severity",
                                                "high",
                                            ],
                                        },
                                        "then": SEVERITY_RANK["high"],
                                    },
                                    {
                                        "case": {
                                            "$eq": [
                                                "$severity",
                                                "medium",
                                            ],
                                        },
                                        "then": SEVERITY_RANK["medium"],
                                    },
                                    {
                                        "case": {
                                            "$eq": [
                                                "$severity",
                                                "low",
                                            ],
                                        },
                                        "then": SEVERITY_RANK["low"],
                                    },
                                ],
                                "default": 4,
                            },
                        },
                    },
                },
                {
                    "$sort": {
                        "severity_rank": rank_direction,
                        "created_at": DESCENDING,
                        "_id": DESCENDING,
                    },
                },
                {
                    "$skip": skip,
                },
                {
                    "$limit": limit,
                },
            ]

            results: list[dict[str, Any]] = []

            async for doc in self._collection.aggregate(pipeline):
                doc["id"] = str(doc.pop("_id"))
                doc.pop("severity_rank", None)
                results.append(doc)

            return results, total

        # --------------------------------------------------------------
        # NORMAL SORT
        # --------------------------------------------------------------

        direction = (
            ASCENDING
            if order == "asc"
            else DESCENDING
        )

        sort_field = {
            "created_at": "created_at",
            "updated_at": "updated_at",
            "file": "file",
            "title": "title",
            "repository_name": "repository_id",
            "rule_id": "rule_id",
        }.get(
            sort,
            "created_at",
        )

        cursor = (
            self._collection
            .find(query)
            .sort(
                [
                    (sort_field, direction),
                    ("_id", DESCENDING),
                ]
            )
            .skip(skip)
            .limit(limit)
        )

        results: list[dict[str, Any]] = []

        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)

        return results, total

    # ------------------------------------------------------------------
    # SECURITY COUNTS
    # ------------------------------------------------------------------

    async def count_open_security(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
        repository_id: str | None = None,
    ) -> int:
        active_categories = list(
            categories or SECURITY_CATEGORIES
        )

        query: dict[str, Any] = {
            "organization_id": organization_id,
            "category": {
                "$in": active_categories,
            },
            "status": "open",
        }

        if repository_id:
            query["repository_id"] = repository_id

        return await self._collection.count_documents(query)

    async def count_by_category(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
    ) -> dict[str, int]:
        active_categories = list(
            categories or SECURITY_CATEGORIES
        )

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": {
                        "$in": active_categories,
                    },
                },
            },
            {
                "$group": {
                    "_id": "$category",
                    "count": {
                        "$sum": 1,
                    },
                },
            },
        ]

        counts = {
            category: 0
            for category in active_categories
        }

        async for row in self._collection.aggregate(pipeline):
            category = str(row.get("_id", ""))

            if category in counts:
                counts[category] = int(
                    row.get("count", 0)
                )

        return counts

    async def count_repositories_with_findings(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
    ) -> int:
        active_categories = list(
            categories or SECURITY_CATEGORIES
        )

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": {
                        "$in": active_categories,
                    },
                },
            },
            {
                "$group": {
                    "_id": "$repository_id",
                },
            },
            {
                "$count": "total",
            },
        ]

        async for row in self._collection.aggregate(pipeline):
            return int(row.get("total", 0))

        return 0

    async def count_by_repository(
        self,
        organization_id: str,
        *,
        categories: list[str] | None = None,
    ) -> dict[str, int]:
        active_categories = list(
            categories or SECURITY_CATEGORIES
        )

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": {
                        "$in": active_categories,
                    },
                },
            },
            {
                "$group": {
                    "_id": "$repository_id",
                    "count": {
                        "$sum": 1,
                    },
                },
            },
        ]

        counts: dict[str, int] = {}

        async for row in self._collection.aggregate(pipeline):
            repo_id = str(row.get("_id", ""))

            if repo_id:
                counts[repo_id] = int(
                    row.get("count", 0)
                )

        return counts

    # ------------------------------------------------------------------
    # QUALITY
    # ------------------------------------------------------------------

    async def list_quality_paginated(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        rule_id: str | None = None,
        q: str | None = None,
        repository_ids_for_search: list[str] | None = None,
        sort: str = "severity",
        order: str = "desc",
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        return await self.list_security_paginated(
            organization_id,
            categories=list(QUALITY_CATEGORIES),
            repository_id=repository_id,
            severity=severity,
            status=status,
            rule_id=rule_id,
            q=q,
            repository_ids_for_search=repository_ids_for_search,
            sort=sort,
            order=order,
            skip=skip,
            limit=limit,
        )

    async def count_open_for_categories(
        self,
        organization_id: str,
        *,
        categories: list[str],
        repository_id: str | None = None,
    ) -> int:
        query: dict[str, Any] = {
            "organization_id": organization_id,
            "category": {
                "$in": categories,
            },
            "status": "open",
        }

        if repository_id:
            query["repository_id"] = repository_id

        return await self._collection.count_documents(query)

    # ------------------------------------------------------------------
    # ANALYTICS
    # ------------------------------------------------------------------

    async def top_rules(
        self,
        organization_id: str,
        *,
        categories: list[str],
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        from app.lib.quality_helpers import highest_severity

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": {
                        "$in": categories,
                    },
                },
            },
            {
                "$group": {
                    "_id": {
                        "rule_id": "$rule_id",
                        "analyzer": "$metadata.engine",
                    },
                    "count": {
                        "$sum": 1,
                    },
                    "severities": {
                        "$push": "$severity",
                    },
                    "repositories": {
                        "$addToSet": "$repository_id",
                    },
                },
            },
            {
                "$sort": {
                    "count": -1,
                },
            },
            {
                "$limit": max(1, min(limit, 100)),
            },
        ]

        results: list[dict[str, Any]] = []

        async for row in self._collection.aggregate(pipeline):
            rule_key = row.get("_id", {})

            severities = [
                str(s)
                for s in row.get("severities", [])
            ]

            results.append(
                {
                    "rule_id": str(
                        rule_key.get("rule_id")
                        or "unknown"
                    ),
                    "analyzer": rule_key.get("analyzer"),
                    "count": int(
                        row.get("count", 0)
                    ),
                    "highest_severity": (
                        highest_severity(severities)
                        or "low"
                    ),
                    "repository_count": len(
                        row.get("repositories", [])
                    ),
                }
            )

        return results

    async def repository_stats(
        self,
        organization_id: str,
        *,
        categories: list[str],
    ) -> list[dict[str, Any]]:
        from app.lib.quality_helpers import highest_severity

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": {
                        "$in": categories,
                    },
                },
            },
            {
                "$group": {
                    "_id": "$repository_id",
                    "count": {
                        "$sum": 1,
                    },
                    "open_count": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$eq": [
                                        "$status",
                                        "open",
                                    ],
                                },
                                1,
                                0,
                            ],
                        },
                    },
                    "severities": {
                        "$push": "$severity",
                    },
                },
            },
            {
                "$sort": {
                    "count": -1,
                },
            },
        ]

        results: list[dict[str, Any]] = []

        async for row in self._collection.aggregate(pipeline):
            severities = [
                str(s)
                for s in row.get("severities", [])
            ]

            results.append(
                {
                    "repository_id": str(
                        row.get("_id", "")
                    ),
                    "finding_count": int(
                        row.get("count", 0)
                    ),
                    "open_count": int(
                        row.get("open_count", 0)
                    ),
                    "highest_severity": highest_severity(
                        severities
                    ),
                }
            )

        return results

    # ------------------------------------------------------------------
    # SINGLE FINDING
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        finding_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(finding_id)
        except Exception:
            return None

        doc = await self._collection.find_one(
            {
                "_id": object_id,
                "organization_id": organization_id,
            }
        )

        if not doc:
            return None

        doc["id"] = str(doc.pop("_id"))

        return doc

    # ------------------------------------------------------------------
    # DEPENDENCY ANALYTICS
    # ------------------------------------------------------------------

    async def dependency_package_keys_for_severity(
        self,
        organization_id: str,
        severity: str,
    ) -> list[dict[str, str]]:
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": "dependency",
                    "severity": severity,
                },
            },
            {
                "$group": {
                    "_id": {
                        "repository_id": "$repository_id",
                        "package_name": "$metadata.package",
                    },
                },
            },
        ]

        results: list[dict[str, str]] = []

        async for row in self._collection.aggregate(pipeline):
            key = row.get("_id", {})

            package_name = key.get("package_name")
            repository_id = key.get("repository_id")

            if package_name and repository_id:
                results.append(
                    {
                        "repository_id": str(repository_id),
                        "package_name": str(package_name),
                    }
                )

        return results

    async def dependency_package_severity_map(
        self,
        organization_id: str,
    ) -> dict[tuple[str, str], str]:
        from app.lib.quality_helpers import highest_severity

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": "dependency",
                },
            },
            {
                "$group": {
                    "_id": {
                        "repository_id": "$repository_id",
                        "package_name": "$metadata.package",
                    },
                    "severities": {
                        "$push": "$severity",
                    },
                },
            },
        ]

        results: dict[tuple[str, str], str] = {}

        async for row in self._collection.aggregate(pipeline):
            key = row.get("_id", {})

            package_name = key.get("package_name")
            repository_id = key.get("repository_id")

            if not package_name or not repository_id:
                continue

            severity = highest_severity(
                [
                    str(s)
                    for s in row.get("severities", [])
                ]
            )

            if severity:
                results[
                    (
                        str(repository_id),
                        str(package_name),
                    )
                ] = severity

        return results

    async def dependency_highest_severity_by_repository(
        self,
        organization_id: str,
    ) -> dict[str, str]:
        from app.lib.quality_helpers import highest_severity

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": "dependency",
                },
            },
            {
                "$group": {
                    "_id": "$repository_id",
                    "severities": {
                        "$push": "$severity",
                    },
                },
            },
        ]

        results: dict[str, str] = {}

        async for row in self._collection.aggregate(pipeline):
            repo_id = row.get("_id")

            if not repo_id:
                continue

            severity = highest_severity(
                [
                    str(s)
                    for s in row.get("severities", [])
                ]
            )

            if severity:
                results[str(repo_id)] = severity

        return results

    async def dependency_top_packages(
        self,
        organization_id: str,
        *,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        from app.lib.quality_helpers import highest_severity

        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "category": "dependency",
                },
            },
            {
                "$group": {
                    "_id": "$metadata.package",
                    "count": {
                        "$sum": 1,
                    },
                    "severities": {
                        "$push": "$severity",
                    },
                    "repositories": {
                        "$addToSet": "$repository_id",
                    },
                    "vulnerability": {
                        "$first": "$rule_id",
                    },
                },
            },
            {
                "$sort": {
                    "count": -1,
                },
            },
            {
                "$limit": max(1, min(limit, 100)),
            },
        ]

        results: list[dict[str, Any]] = []

        async for row in self._collection.aggregate(pipeline):
            package_name = row.get("_id")

            if not package_name:
                continue

            severities = [
                str(s)
                for s in row.get("severities", [])
            ]

            count = int(
                row.get("count", 0)
            )

            results.append(
                {
                    "package_name": str(package_name),
                    "count": count,
                    "vulnerable_count": count,
                    "highest_severity": (
                        highest_severity(severities)
                        or "low"
                    ),
                    "repository_count": len(
                        row.get("repositories", [])
                    ),
                    "vulnerability": row.get(
                        "vulnerability"
                    ),
                }
            )

        return results

    # ------------------------------------------------------------------
    # AI EXPLANATION
    # ------------------------------------------------------------------

    async def update_ai_explanation(
        self,
        finding_id: str,
        organization_id: str,
        explanation: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(finding_id)
        except Exception:
            return None

        result = await self._collection.find_one_and_update(
            {
                "_id": object_id,
                "organization_id": organization_id,
            },
            {
                "$set": {
                    "ai_explanation": explanation,
                    "updated_at": datetime.now(UTC),
                },
            },
            return_document=ReturnDocument.AFTER,
        )

        if not result:
            return None

        result["id"] = str(
            result.pop("_id")
        )

        return result