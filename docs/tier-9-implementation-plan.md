# Tier 9 — Analysis Operations & Run Intelligence

## Existing foundation

- `analysis_runs` collection with lifecycle `queued → running → complete | failed`
- Per-repo list/detail at `/repositories/{id}/analysis-runs`
- `AnalysisPipeline` creates snapshots on success (Tier 8)
- Dashboard `analysis_activity` (8 recent runs, limited fields)
- Repository detail has basic paginated history

## Gaps addressed

1. Org-wide `/api/v1/analysis-runs` with server-side filters, sort, pagination
2. Global detail with snapshot linkage and analyzer execution breakdown
3. Retry failed runs; cancel queued runs (run created at queue time)
4. Enhanced `analyzer_summary` with executed / skipped / failed
5. `/app/analysis-runs` list + detail pages with live polling
6. Dashboard + repository detail integration

## API

| Method | Path | RBAC |
|--------|------|------|
| GET | `/analysis-runs` | Viewer+ |
| GET | `/analysis-runs/{id}` | Viewer+ |
| POST | `/analysis-runs/{id}/retry` | Member+ |
| POST | `/analysis-runs/{id}/cancel` | Member+ |

## Indexes

- `(organization_id, started_at DESC)`
- `(organization_id, repository_id, started_at DESC)`
- `(organization_id, status, started_at DESC)`
- `(organization_id, trigger, started_at DESC)`

## Cancel semantics

Runs are created at queue time with `status=queued`. Cancel is allowed only while `queued`. Running analyses cannot be safely cancelled without Celery revoke.

## Testing

Backend: `test_analysis_runs.py` (~15 tests). Frontend: list, detail, polling, RBAC, snapshot linkage.
