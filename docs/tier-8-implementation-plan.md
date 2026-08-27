# Tier 8 — Historical Intelligence + Analytics Foundation

## 1. Existing analytics architecture

- **API:** `GET /api/v1/analytics?range=30d` → `AnalyticsService.get_summary()`
- **Service:** Thin wrapper over `DashboardService`; returns current snapshot scores only
- **Frontend:** `analytics-page.tsx` — four `MetricCard`s + text-only trend direction
- **Dashboard:** `DashboardService.get_dashboard()` aggregates live repo/finding/PR state; `trends` section is stubbed (`available: false`)
- **Per-repo history:** `GET /api/v1/repositories/{id}/health-history` reads `analysis_runs.health_snapshot` (limit 20)

## 2. Existing analysis lifecycle

```
queued → running → complete | failed
```

`AnalysisPipeline.run()`:
1. Creates `analysis_runs` document
2. Clones repo, runs scanners
3. **`replace_for_analysis`** on findings + dependencies (wipes prior rows)
4. Computes scores, updates `repositories`
5. Stores `health_snapshot` on `analysis_runs` via `mark_complete`
6. Scores open PRs (errors swallowed)

Failed runs do not update scores to complete; findings may be partially replaced.

## 3. Existing persisted metrics

| Source | Metrics |
|--------|---------|
| `repositories` | health, security, quality, dependency scores; risk_level; finding counts |
| `analysis_runs.health_snapshot` | scores, severity_counts, recorded_at |
| `findings` | Current run only (replaced each analysis) |
| `dependencies` | Current run only |
| `pull_requests` | risk_score, risk_level (overwritten on rescore) |

## 4. What is lost between analyses

- All prior finding rows and user triage state (status, AI explanations)
- All prior dependency rows
- Repository scores (overwritten)
- Per-category finding history (except aggregate `severity_counts` in `health_snapshot`)
- Cross-run deltas, trends, regressions

## 5. Proposed historical model

**Collection:** `analysis_snapshots`

One immutable document per successful `analysis_run_id` (unique index). Captures scores, per-category finding severity breakdowns, dependency counts, PR metrics, and `analyzer_summary` at completion time.

**Null semantics:** `null` = not measured; `0` = zero.

## 6. Required indexes

| Index | Purpose |
|-------|---------|
| `(analysis_run_id)` UNIQUE | Idempotent snapshot creation |
| `(organization_id, repository_id, captured_at DESC)` | Repo time-series queries |
| `(organization_id, captured_at DESC)` | Org-wide trends with date filter |
| `(repository_id, captured_at DESC)` | Repo-scoped history |

## 7. API changes

| Endpoint | Change |
|----------|--------|
| `GET /api/v1/analytics/overview` | **New** — baseline, trends, comparisons, regressions, improvements |
| `GET /api/v1/analytics` | **Kept** — derives trend direction from historical service when possible |

Query params: `repositoryId`, `from`, `to` (max 365 days, default 90).

## 8. Frontend changes

- Install `recharts` (lightweight, React-native)
- Rebuild `analytics-page.tsx` with baseline UX, filters, charts, comparison table, regressions/improvements
- New types + `analyticsApi.overview()`

## 9. Migration/backfill strategy

- Script: `python -m app.scripts.backfill_analysis_snapshots [--dry-run] [--organization-id] [--repository-id]`
- Backfill from completed `analysis_runs` with `health_snapshot` only when reconstructable
- Per-category finding breakdowns remain `null` in backfilled snapshots (insufficient source data)
- Idempotent via `analysis_run_id` unique index

## 10. Testing strategy

**Backend:** snapshot lifecycle, idempotency, isolation, trends, filters, baseline states, delta/regression/improvement logic, null handling

**Frontend:** baseline empty/established/trend states, chart summaries, filters, comparison table, regressions

## 11. Performance strategy

- MongoDB aggregation for org/repo time-series; limit points (default 90 days, max 365)
- No `fetchAllPages` / `page_size=10000`
- Single overview request for analytics page
- Repository comparisons via aggregation (latest + previous per repo)
