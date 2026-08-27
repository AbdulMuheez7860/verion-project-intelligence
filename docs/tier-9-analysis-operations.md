# Tier 9 — Analysis Operations & Run Intelligence

## Overview

Tier 9 makes analysis runs a first-class operational entity connecting repository → execution → analyzer results → snapshot → historical intelligence.

## API

| Method | Path | RBAC |
|--------|------|------|
| GET | `/api/v1/analysis-runs` | Viewer+ |
| GET | `/api/v1/analysis-runs/{id}` | Viewer+ |
| POST | `/api/v1/analysis-runs/{id}/retry` | Member+ |
| POST | `/api/v1/analysis-runs/{id}/cancel` | Member+ |

### List filters

- `repositoryId`, `status`, `trigger` (manual/webhook/scheduled)
- `q` — repository name or commit SHA prefix
- `from`, `to` — ISO date range on `started_at`
- `sort` — started | completed | duration | status
- `order` — asc | desc

## Lifecycle

1. `queue_analysis` creates run with `status=queued` and enqueues Celery with `analysis_run_id`
2. Worker marks `running`, executes pipeline, creates snapshot on success
3. Cancel allowed only while `queued` (marks failed with "Cancelled by user.")
4. Retry queues new run for same repository when prior run failed

## Analyzer summary

```json
{
  "executed": ["ruff", "eslint"],
  "skipped": [{ "name": "semgrep", "reason": "Unsupported for this repository" }],
  "failed": [],
  "dependency_scan": true
}
```

## Frontend

- `/app/analysis-runs` — paginated list with URL-persisted filters
- `/app/analysis-runs/:analysisId` — detail with polling, retry/cancel, snapshot linkage
- Legacy `/app/repositories/:id/analysis/:analysisId` redirects to global detail

## Indexes

- `(organization_id, started_at DESC)`
- `(organization_id, repository_id, started_at DESC)`
- `(organization_id, status, started_at DESC)`
- `(organization_id, trigger, started_at DESC)`

## Known limitations

- Running analyses cannot be cancelled (Celery revoke not implemented)
- Scheduled trigger filter exists but no Celery Beat jobs yet
- Findings-by-category on detail only for latest complete run
