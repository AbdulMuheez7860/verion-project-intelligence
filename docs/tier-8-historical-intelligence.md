# Tier 8 — Historical Intelligence

## Architecture

Tier 8 introduces immutable **`analysis_snapshots`** created at the end of each successful repository analysis. Snapshots preserve engineering metrics that would otherwise be lost when findings and dependencies are replaced on subsequent runs.

```
Analysis completes
  → findings/dependencies persisted
  → scores computed
  → PR risk rescored
  → analysis_snapshot created (idempotent on analysis_run_id)
  → analysis_run marked complete
```

Historical intelligence is served by `HistoricalIntelligenceService` and exposed via `GET /api/v1/analytics/overview`.

## Snapshot schema

Collection: `analysis_snapshots`

| Field | Description |
|-------|-------------|
| `organization_id`, `repository_id`, `analysis_run_id` | Scope + idempotency key |
| `captured_at` | When snapshot was taken |
| `health_score`, `security_score`, `quality_score`, `dependency_score`, `pr_risk_score` | Scores at analysis time |
| `finding_counts` | Total severity breakdown |
| `security_findings`, `quality_findings`, `dependency_findings` | Per-category severity |
| `dependency_counts` | total / vulnerable / outdated / healthy |
| `pull_request_metrics` | open / high_risk / critical_risk / average_risk_score |
| `analyzer_summary` | Scanners executed |

**Null vs zero:** `null` means not measured; `0` means zero.

## Snapshot lifecycle

- Created only after successful analysis
- Not created for failed runs
- Idempotent on `analysis_run_id` (unique index)
- Immutable after insert

## Metric semantics

| Metric | Better direction |
|--------|------------------|
| health_score, security_score, quality_score, dependency_score | Higher |
| finding counts, PR risk | Lower |

Material change thresholds:
- Scores: ±5 points
- Counts: ±1

## Trend calculation

Trend points are real snapshots within the requested date range (default 90 days, max 365). No interpolation.

Baseline states:
- **0 snapshots:** Building your baseline
- **1 snapshot:** Baseline established (no trend lines)
- **2+ snapshots:** Full trends

## API

### `GET /api/v1/analytics/overview`

Query params: `repositoryId`, `from`, `to`

Returns baseline, freshness, score trends, finding trends, repository comparisons, regressions, improvements.

### `GET /api/v1/analytics` (legacy)

Unchanged contract; now derives `trend_direction` and `analysis_runs_count` from snapshot data when available.

## Migration / backfill

```bash
python -m app.scripts.backfill_analysis_snapshots --dry-run
python -m app.scripts.backfill_analysis_snapshots
```

Backfills from `analysis_runs.health_snapshot` where available. Per-category breakdowns remain `null` for backfilled records.

## Indexes

- `analysis_run_id` (unique)
- `(organization_id, repository_id, captured_at DESC)`
- `(organization_id, captured_at DESC)`
- `(repository_id, captured_at DESC)`

## Known limitations

- Historical data begins when Tier 8 is deployed (or after backfill from runs with `health_snapshot`)
- Backfilled snapshots lack per-category finding breakdowns and PR metrics
- Delivery metrics (PR throughput, merge frequency) remain unimplemented
- Org-wide trends may include multiple snapshots per day from different repositories
