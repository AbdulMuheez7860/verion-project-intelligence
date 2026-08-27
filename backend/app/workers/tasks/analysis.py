import asyncio
import logging
from typing import Any

from app.core.database import close_client, get_database
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.dependencies import DependencyRepository
from app.repositories.findings import FindingRepository
from app.repositories.integrations import IntegrationRepository
from app.repositories.memberships import MembershipRepository
from app.repositories.notification_preferences import NotificationPreferencesRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.pull_requests import PullRequestRepository
from app.repositories.repositories import RepositoryRepository
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.analysis_snapshot_service import AnalysisSnapshotService
from app.services.notification_events import NotificationEventService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def enqueue_analysis(
    repository_id: str,
    organization_id: str,
    *,
    trigger: str = "manual",
    analysis_run_id: str | None = None,
) -> None:
    run_analysis.delay(repository_id, organization_id, trigger, analysis_run_id)


@celery_app.task(
    name="verion.run_analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=60 * 25,
    time_limit=60 * 30,
)
def run_analysis(
    self,
    repository_id: str,
    organization_id: str,
    trigger: str = "manual",
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    try:
        return asyncio.run(
            _run_analysis_async(repository_id, organization_id, trigger, analysis_run_id),
        )
    except ValueError as exc:
        logger.warning("Analysis failed permanently: %s", exc)
        return {"status": "failed", "error": str(exc)}
    except Exception as exc:
        logger.exception("Analysis task failed, retrying")
        raise self.retry(exc=exc) from exc


async def _run_analysis_async(
    repository_id: str,
    organization_id: str,
    trigger: str,
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    db = get_database()
    repo_repo = RepositoryRepository(db)
    analysis_runs = AnalysisRunRepository(db)
    snapshot_service = AnalysisSnapshotService(AnalysisSnapshotRepository(db))
    notification_events = NotificationEventService(
        NotificationRepository(db),
        NotificationPreferencesRepository(db),
        MembershipRepository(db),
        PullRequestRepository(db),
        AnalysisSnapshotRepository(db),
    )
    pipeline = AnalysisPipeline(
        repositories=repo_repo,
        analysis_runs=analysis_runs,
        findings=FindingRepository(db),
        dependencies=DependencyRepository(db),
        pull_requests=PullRequestRepository(db),
        integrations=IntegrationRepository(db),
        snapshot_service=snapshot_service,
        notification_events=notification_events,
    )
    try:
        return await pipeline.run(
            repository_id,
            organization_id,
            trigger,
            analysis_run_id=analysis_run_id,
        )
    except Exception as exc:
        latest = await analysis_runs.latest_for_repository(repository_id, organization_id)
        if latest and latest.get("status") not in {"failed", "complete"}:
            await analysis_runs.mark_failed(latest["id"], error=str(exc))
        await repo_repo.update_analysis_status(repository_id, organization_id, status="failed")
        raise
    finally:
        await close_client()
