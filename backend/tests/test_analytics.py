from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.core.database import get_database
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.services.analytics import AnalyticsService
from app.services.dashboard import DashboardService
from app.services.historical_intelligence import HistoricalIntelligenceService
from app.services.repositories import RepositoryService


@pytest.mark.asyncio
async def test_analytics_summary_reflects_dashboard_baseline():
    db = get_database()
    organization_id = str(ObjectId())
    repository_id = str(ObjectId())

    await db["analysis_runs"].insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "repository_id": repository_id,
            "status": "complete",
            "trigger": "manual",
            "created_at": datetime.now(UTC),
        },
    )
    await db["repositories"].insert_one(
        {
            "_id": ObjectId(repository_id),
            "organization_id": organization_id,
            "name": "api-service",
            "full_name": "acme/api-service",
            "owner": "acme",
            "health_score": 84.0,
            "security_score": 90.0,
            "code_quality_score": 78.0,
        },
    )

    repo_repo = RepositoryRepository(db)
    pr_repo = PullRequestRepository(db)
    dashboard_service = DashboardService(
        repo_repo,
        pr_repo,
        RepositoryService(repo_repo, pr_repo),
        FindingRepository(db),
        AnalysisRunRepository(db),
        DependencyRepository(db),
    )
    historical = HistoricalIntelligenceService(
        AnalysisSnapshotRepository(db),
        repo_repo,
        AnalysisRunRepository(db),
        pr_repo,
    )
    service = AnalyticsService(dashboard_service, historical)

    summary = await service.get_summary(organization_id, "30d")

    assert summary.has_analysis_data is True
    assert summary.current_health == 84.0
    assert summary.current_security == 90.0
    assert summary.current_quality == 78.0
    assert summary.trend_direction == "unavailable"
    assert summary.message is not None
