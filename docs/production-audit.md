# Verion Production Audit

**Phase 0 — Read-only audit**  
**Date:** August 12, 2026  
**Scope:** `frontend/`, `backend/`, `design-reference/`, `docs/`, Docker, configuration, tests, Cursor rules  
**Constraint:** No application code was modified to produce this document.

---

## Executive Summary

Verion is a **real, layered engineering intelligence platform** — not a decorative mock dashboard. The backend runs actual scanners (Semgrep, Bandit, Ruff, ESLint, detect-secrets, pip-audit), persists findings in MongoDB, scores repositories and pull requests deterministically, and exposes typed REST APIs. The frontend fetches live data via cookie-based auth and generally shows honest empty/unavailable states instead of fabricated metrics.

The product is **not production-ready** as a complete platform. It is a strong **v1 application core** with significant gaps in marketing, premium UX polish, RBAC, operational hardening, CI/CD, and several intentionally stubbed surfaces (password reset, settings). **Historical analytics (Tier 8)** now uses immutable `analysis_snapshots` with real trend charts on `/app/analytics`.

**Why the UI feels generic today**

1. Repeated page template: `PageHeader` → 2–4 `MetricCard`s → bordered `Card` → table — same rhythm on every screen.
2. ~~No data visualization library; “Analytics” is text-only with no charts.~~ **Resolved (Tier 8):** Recharts-based trend charts on `/app/analytics` backed by `analysis_snapshots`.
3. Decorative affordances: topbar “Search” + `⌘K` with no command palette; help/settings full of disabled controls.
4. Dead primary CTAs: `AnalyzeRepositoryButton` appears on most pages without `onClick` (only wired on repository detail).
5. No public marketing site — `/` redirects straight into the authenticated app.
6. Minimal design system usage: 6 shadcn primitives; Radix dialog/dropdown/checkbox installed but unused.
7. Default Vite favicon and generic “V” monogram logo.
8. Workspace-wide domain pages (security/quality/deps) rather than repo-scoped workflows from repository detail.
9. Hollow secondary surfaces: notifications, team settings, profile save (local fake success).

**What is genuinely working**

- Auth signup/login/refresh/logout with HTTP-only cookies
- GitHub OAuth connect, repository connect, webhook ingestion (when configured)
- Celery-backed repository analysis with real scanner subprocesses
- Normalized findings, dependency records, repo health scores, PR risk engine with explainable factors
- AI finding explanations (optional, provider-agnostic) that consume real findings only
- Purpose-driven page copy (`PAGE_PURPOSE`) on major app screens
- MongoDB index initialization (recently fixed: no invalid explicit `_id` index)

---

## 1. Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Browser (React + Vite)                          │
│  Cookie auth · useAsyncData · /api proxy (dev) · VITE_API_URL (prod)   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / fetch credentials:include
┌───────────────────────────────────▼─────────────────────────────────────┐
│                    FastAPI (app/main.py)                                │
│  Routers: auth, integrations, repositories, analysis, findings,         │
│           analytics, webhooks                                           │
│  Lifespan: MongoDB ping + ensure_indexes()                              │
└───────┬─────────────────────────────┬───────────────────────────────────┘
        │                             │
        ▼                             ▼
┌───────────────┐              ┌────────────────┐
│   MongoDB     │              │     Redis      │
│  (Motor async)│              │ OAuth state    │
│  10 collections│             │ Celery broker  │
└───────────────┘              │ Celery results │
        ▲                      └────────┬───────┘
        │                               │
        │                      ┌────────▼───────┐
        │                      │ Celery worker  │
        │                      │ analysis task  │
        │                      │ webhook task   │
        └──────────────────────┤ git clone +    │
                                 │ scanner CLIs │
                                 └────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              GitHub API          Semgrep/Bandit/      OpenAI-compatible
              OAuth/Webhooks      Ruff/ESLint/etc.     LLM (optional)
```

**Deployment today:** `docker-compose.yml` runs MongoDB, Redis, backend API, and Celery worker. Frontend runs outside Docker (`npm run dev`). No GitHub Actions CI. No root README.

**Design reference:** `design-reference/verion/` — Next.js prototype with mocks and localStorage auth. **Must not be imported into production code.**

---

## 2. Frontend Architecture

### Structure (`frontend/src/`)

| Area | Path | Notes |
|------|------|-------|
| App bootstrap | `app/App.tsx`, `providers.tsx`, `router.tsx` | React Router 7, auth provider |
| API layer | `api/*.ts` | `client.ts` + domain modules; no mock layer |
| Features | `features/*/` | One folder per product area (~12 feature modules) |
| Components | `components/` | layout, navigation, tables, states, ui, risk, findings |
| Hooks | `hooks/` | `use-auth`, `use-async-data`, `use-theme` |
| Types | `types/api.ts` | Single consolidated API contract (~240 lines) |
| Design tokens | `styles/index.css` | Tailwind v4, OKLCH, light/dark, Inter 13px base |
| Lib | `lib/` | `page-purpose`, `format-score`, `risk-tone`, `utils` |

**Scale:** ~72 source files, 3 test files.

### Data fetching pattern

- `useAsyncData(fetcher, deps)` — loading/error/success + `isUnavailable` for network/404/5xx
- All metrics bind to API responses; `MetricCard` shows `—` when value is null/undefined
- **No production mock arrays** in page components
- Theme persisted in `localStorage` only (not auth)

### Component library gap

**Implemented shadcn-style primitives:** `button`, `input`, `label`, `card`, `badge`, `skeleton`

**Installed but unused:** `@radix-ui/react-checkbox`, `dialog`, `dropdown-menu`, `separator`

**Missing for planned UX:** command palette, dialogs/sheets for mobile nav, tabs for repository detail, chart components, toast notifications, data table pagination controls

---

## 3. Backend Architecture

### Layering (correct separation)

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Routers | `app/api/*.py` | HTTP validation, auth deps, response mapping |
| Services | `app/services/*.py` | Business logic, orchestration, scoring |
| Repositories | `app/repositories/*.py` | MongoDB queries scoped by `organization_id` |
| Schemas | `app/schemas/*.py` | Pydantic models, camelCase JSON via `APIModel` |
| Workers | `app/workers/` | Celery tasks for analysis + webhooks |
| Analyzers | `app/analyzers/` | CLI wrappers + orchestrator + normalization |
| Integrations | `app/integrations/github/`, `llm/` | GitHub client, webhook verify, LLM provider |

### Key services

| Service | File | Status |
|---------|------|--------|
| Auth | `services/auth.py` | Signup, login, session |
| GitHub integration | `services/github_integration.py` | OAuth, token storage |
| Repositories | `services/repositories.py` | Connect, disconnect, analyze queue |
| Analysis pipeline | `services/analysis_pipeline.py` | Clone → scan → persist → score |
| Risk engine (repo) | `services/risk_engine.py` | Health/security/quality from findings |
| PR risk | `services/pr_risk_engine.py`, `pr_risk_service.py` | Explainable PR score |
| Dashboard | `services/dashboard.py` | Engineering overview aggregation |
| Findings | `services/findings.py` | Security/quality/dependency summaries |
| Analytics | `services/analytics.py`, `services/historical_intelligence.py` | Snapshot + trends from `analysis_snapshots`; `GET /analytics/overview` |
| Finding AI | `services/finding_ai.py` | Explain existing findings |

### Dead / unused code

- `app/schemas/analysis.py` — domain types not referenced elsewhere
- `app/utils/ids.py` → `serialize_doc()` — unused
- `workers/tasks/webhooks.py` → `_noop()` — unused
- Duplicate `FindingRepository` import in `analysis_pipeline.py`

---

## 4. Database Architecture

### Collections

| Collection | Purpose | Tenant key |
|------------|---------|------------|
| `users` | Accounts | `_id` |
| `organizations` | Workspaces | `_id` |
| `memberships` | User↔org roles | `organization_id` |
| `integrations` | GitHub OAuth tokens (encrypted) | `organization_id` |
| `repositories` | Connected repos + scores | `organization_id` |
| `pull_requests` | Synced PRs + risk scores | `organization_id` |
| `webhook_deliveries` | Idempotency (`_id` = delivery UUID) | `organization_id` |
| `findings` | Normalized scanner output | `organization_id` |
| `analysis_runs` | Run status/history | `organization_id` |
| `dependencies` | Package vulnerability records | `organization_id` |

### Indexes (`app/core/indexes.py`)

Created at startup via `ensure_indexes()`:

| Collection | Indexes |
|------------|---------|
| `users` | `email` unique |
| `organizations` | `slug` unique |
| `memberships` | `(user_id, organization_id)` unique |
| `integrations` | `(organization_id, provider)` unique |
| `repositories` | `(organization_id, name)`; `(organization_id, github_id)` unique; `full_name` |
| `pull_requests` | `(organization_id, github_id)` unique |
| `findings` | `(organization_id, repository_id)`; `(organization_id, category, severity)` |
| `analysis_runs` | `(organization_id, repository_id, created_at DESC)` |
| `dependencies` | `(organization_id, repository_id)` |

**`webhook_deliveries`:** No explicit index — relies on MongoDB’s automatic unique `_id` index (correct).

**Missing indexes for future scale:**

- `pull_requests` by `risk_score` (dashboard sorts in memory)
- `findings` by `status`, `rule_id` for filtered security workflows
- TTL on `webhook_deliveries` for retention
- Pagination cursors — most list endpoints return full collections

### Data lifecycle

- **Historical analytics (Tier 8):** Each successful analysis creates an immutable `analysis_snapshots` document with scores, finding counts, dependency counts, and PR metrics at capture time. Trends, regressions, and comparisons derive from snapshots — not from mutable current findings.
- Findings and dependencies remain **mutable current state** per repository (replaced on each analysis); historical finding-level diffs are not stored — only aggregated snapshot metrics.
- `analysis_runs` stored; snapshot links via `analysis_run_id` (unique index). List run history API/UI still not exposed.

---

## 5. Authentication Architecture

### Mechanism

- **JWT in HTTP-only cookies** (not server-side session store)
  - Access: `verion_session` — 15 minutes
  - Refresh: `verion_refresh` — 7 days
- Algorithm: HS256 (`python-jose`)
- Passwords: bcrypt (`passlib`)
- Cookies: `httponly=True`, `samesite=lax`, `secure=not settings.debug`

### Organization model

- Single workspace per user: `user.organization_id` on user document
- Signup creates user + organization + owner membership atomically
- **No workspace switcher**, no multi-org membership UX

### RBAC

- `MembershipRole`: `owner | admin | member | viewer` — **defined but not enforced**
- All authenticated org members can connect repos, trigger analysis, call AI explain
- No role-based route guards on backend or frontend

### Stubs

| Endpoint | Status |
|----------|--------|
| `POST /auth/forgot-password` | Returns 204, no email |
| `POST /auth/reset-password` | Returns 204, no token validation |

### Config mismatch

- `settings.session_cookie_name` / `refresh_cookie_name` exist but deps hardcode `verion_session` / `verion_refresh`
- `bcrypt_rounds` setting unused

---

## 6. GitHub Integration Architecture

### OAuth flow

1. `GET /integrations/github/connect` → redirect to GitHub
2. State stored in Redis (`OAuthStateStore`, 10 min TTL)
3. `GET /integrations/github/callback` → exchange code, encrypt token, upsert `integrations`
4. Redirect to frontend settings

### Repository connect

- `POST /repositories` with `githubId`
- Creates repo doc, registers webhook (if `GITHUB_WEBHOOK_SECRET` set), queues analysis

### Webhooks

- `POST /webhooks/github` — verifies `X-Hub-Signature-256` **only when secret is configured**
- Resolves repo by `full_name` (global lookup, org derived from repo doc)
- Queues Celery `process_github_webhook`
- Idempotency via `webhook_deliveries` insert with delivery ID as `_id`

### Gaps

- Disconnect GitHub integration does not remove connected repositories or webhooks
- PR lifecycle: open PRs synced; closed/merged not updated in DB
- Webhook events beyond `push`/`pull_request` ignored (no PR metadata sync)
- No GitHub App support (OAuth App only)
- `GITHUB_WEBHOOK_SECRET` defaults to `dev-webhook-secret` in docker-compose

---

## 7. Analysis Architecture

### Pipeline (`services/analysis_pipeline.py`)

```
queued → running → complete | failed
  1. Create analysis_runs document
  2. Fetch GitHub token, sync repo metadata + open PRs
  3. git clone (depth 1, token in URL)
  4. Run orchestrator + dependency analyzer
  5. Replace findings + dependencies in MongoDB
  6. compute_risk_metrics → update repository scores
  7. Score open PRs (errors silently swallowed)
  8. Mark run complete/failed
```

### Analyzers (`analyzers/orchestrator.py`)

| Analyzer | Tool | Scope |
|----------|------|-------|
| Semgrep | `semgrep` | All files (`p/default`) |
| Bandit | `bandit` | Python |
| Ruff | `ruff check --output-format json` | Python |
| ESLint | `npx eslint` | JS/TS |
| Secrets | `detect-secrets` | All files |
| Dependencies | `pip-audit` | `requirements.txt` only |

**Orchestrator behavior:** Skips unsupported workspaces; **catches and ignores per-analyzer exceptions** (silent partial failure).

### Gaps

- No `npm audit` / lockfile analysis despite ESLint for JS
- `outdated_count` always 0; `latest_version` equals current
- No PR-scoped analysis (always full repo clone)
- No coverage signal (PR risk `coverage_percent` never populated)
- No analyzer timeouts documented in code review (subprocess risk)
- Celery retries all exceptions (`max_retries=3`) including permanent failures

---

## 8. Risk Engine Architecture

### Repository risk (`services/risk_engine.py`)

- Severity-weighted penalties by category (security/secret/dependency vs quality)
- `health_score = security × 0.6 + quality × 0.4`
- `risk_level` from max severity counts
- Persisted on repository after each analysis

### PR risk (`services/pr_risk_engine.py`)

Deterministic 0–100 score with explainable factors:

- Security findings in changed files
- Change size, complexity
- Coverage (signal exists but never fed)
- Dependency manifest changes + vulnerability count
- Historical repository risk + prior PR average

Stored as `risk_score` + `risk_score_detail` on PR documents.

**API:** `GET /pull-requests/{id}/risk`

**Frontend:** `MergeSafetyVerdict`, `RiskScoreBreakdown` on PR detail — **no changed-files list, no inline findings on PR page**

### Improvement opportunities (Phase 13)

- Factor weights not validated against real team workflows
- No confidence scoring on findings in risk calculation
- No analysis-completeness penalty when scanners fail silently

---

## 9. AI Architecture

### Provider abstraction

- `integrations/llm/base.py` — `LLMProvider` protocol
- `integrations/llm/openai_compatible.py` — OpenAI-compatible API
- `integrations/llm/factory.py` — returns provider or disabled state

### Use case: finding explanations only

- `services/finding_ai.py` — consumes structured finding, returns explanation + remediation
- System prompt forbids inventing findings or changing severity
- Persists `ai_explanation` on finding document
- `POST /findings/{id}/explain?regenerate=`

### Correct boundaries (maintained)

- AI does **not** generate risk scores
- AI does **not** replace scanner findings
- AI unavailable when `LLM_API_KEY` empty — professional error in UI

### Gaps

- No usage logging (tokens, latency, cost)
- No PR summary or dashboard AI features
- `LLM_*` not in `backend/.env.example` (present in config)
- Worker container missing `LLM_*` env (explain is API-path only today)

---

## 10. Current Routes

### Frontend routes (`frontend/src/app/router.tsx`)

| Route | Auth | Page |
|-------|------|------|
| `/` | Protected redirect | → `/app/dashboard` |
| `/login`, `/signup`, `/forgot-password` | Public only | Auth pages |
| `/onboarding` | Protected | Onboarding wizard |
| `/app/dashboard` | Protected | Dashboard |
| `/app/repositories` | Protected | Repository list |
| `/app/repositories/connect` | Protected | Connect flow |
| `/app/repositories/:id` | Protected | Repository detail |
| `/app/pull-requests` | Protected | PR list |
| `/app/pull-requests/:id` | Protected | PR detail |
| `/app/security` | Protected | Security center |
| `/app/code-quality` | Protected | Code quality |
| `/app/dependencies` | Protected | Dependencies |
| `/app/analytics` | Protected | Analytics |
| `/app/notifications` | Protected | Notifications (static empty) |
| `/app/settings/*` | Protected | Settings sub-pages |

**Missing:** `/reset-password`, all marketing routes (`/features`, `/pricing`, `/about`, public `/`)

### Backend API routes (`/api/v1`)

| Group | Endpoints | Auth |
|-------|-----------|------|
| Health | `GET /health`, `GET /api/v1/health` | None |
| Auth | signup, login, refresh, logout, me, forgot/reset (stubs) | Mixed |
| GitHub | status, connect, callback, disconnect, list remote repos | Org |
| Repositories | CRUD, analyze | Org |
| Pull requests | list, get, risk | Org |
| Dashboard | `GET /dashboard` | Org |
| Security/Quality/Deps | summaries + findings lists | Org |
| Findings | get, explain | Org |
| Analytics | `GET /analytics?range=` | Org |
| Webhooks | `POST /webhooks/github` | Signature (conditional) |

**Missing APIs:** finding status updates, org/member management, analysis run history, notifications, global search

---

## 11. Current Features

### Implemented end-to-end

| Feature | Backend | Frontend | Worker |
|---------|---------|----------|--------|
| Signup / login / logout | ✅ | ✅ | — |
| GitHub OAuth connect | ✅ | ✅ | — |
| Connect repository | ✅ | ✅ | — |
| Repository analysis | ✅ | ✅ (detail only) | ✅ |
| Security findings view | ✅ | ✅ | — |
| Quality findings view | ✅ | ✅ | — |
| Dependency view | ✅ | ✅ | — |
| Dashboard overview | ✅ | ✅ | — |
| PR list + risk sort | ✅ | ✅ | — |
| PR merge safety + risk breakdown | ✅ | ✅ | — |
| AI finding explanation | ✅ | ✅ (security table) | — |
| Webhook → re-analyze | ✅ | — | ✅ |
| Dark/light theme | — | ✅ | — |
| Purpose-driven page headers | — | ✅ | — |

### Partially implemented

| Feature | Gap |
|---------|-----|
| Analytics | ✅ Trends, charts, regressions/improvements from `analysis_snapshots` | Date/repo filters; delivery metrics still unavailable |
| Forgot password | API returns 204; no email; no reset route in frontend |
| Onboarding | UI exists; not enforced after signup skip |
| Repository detail | No tabs; links to workspace-wide domain pages |
| PR intelligence | No changed files, no PR-scoped findings table |
| GitHub disconnect | Removes integration doc only |
| Notifications | Static empty page |
| Settings | Profile/team/notifications/security mostly placeholder |

### Not implemented

- Marketing website
- Command palette / global search
- RBAC enforcement
- Rate limiting
- Analysis run history UI/API
- Finding workflow (acknowledge, resolve, false positive)
- npm dependency scanning
- Historical analytics / trend charts ~~(blocked)~~ **Implemented (Tier 8)**
- CI/CD pipeline
- Shareable reports / export
- Email verification
- Multi-workspace support

---

## 12. Broken / Incomplete Features

| Item | Severity | Details |
|------|----------|---------|
| `AnalyzeRepositoryButton` without handler | **High UX** | Dashboard, security, quality, deps, analytics, table empty states |
| Topbar search / ⌘K | **High UX** | Decorative; no command palette |
| Password reset | **Medium** | Backend stubs; no frontend reset page |
| Analytics trends | ~~**Medium**~~ **Resolved (Tier 8)** | Real trends from `analysis_snapshots`; baseline UX for 0/1 snapshots |
| Settings profile save | **Medium** | Fake local success message |
| Help center | **Low** | All cards disabled |
| Settings security/notifications | **Low** | All controls disabled |
| RBAC | **High security** | Roles exist, never checked |
| Webhook verify when secret empty | **High security** | Accepts unsigned payloads |
| GitHub disconnect cleanup | **Medium** | Orphan repos/webhooks |
| PR closed state | **Medium** | Stale open PRs in DB |
| Silent analyzer failures | **Medium** | Partial analysis without user visibility |

---

## 13. Mock / Fake Behavior

### Production code: largely honest

- No random metric generation in frontend pages
- No mock API layer in `frontend/src/api/`
- Backend computes scores from stored findings
- Analytics explicitly reports trend unavailable with message

### Problematic patterns (not fake metrics, but misleading UX)

| Pattern | Location |
|---------|----------|
| Profile “saved” without API | `settings-pages.tsx` |
| `AnalyzeRepositoryButton` renders as actionable but inert | Multiple pages |
| `QualitySummary` schema includes `averageComplexity`, `duplicationPercent`, `technicalDebtHours` — **not exposed in UI after recent cleanup** (good) but fields still in API schema |
| Dashboard severity `?? 0` when `hasData` true | Could conflate missing vs zero |
| Forgot-password always succeeds | User believes email was sent |

### Isolated to design reference (expected)

- `design-reference/verion/lib/mock/index.ts` — all domain data
- `design-reference/verion/lib/auth/demo-auth-adapter.ts` — localStorage auth
- `design-reference/verion/components/verion-app.tsx` — monolithic mocked UI

**No imports from `design-reference/` in production `frontend/src/`** — verified.

---

## 14. Hardcoded Data

| Location | Data | Risk |
|----------|------|------|
| `docker-compose.yml` | `SECRET_KEY`, `GITHUB_WEBHOOK_SECRET` defaults | Dev only; dangerous if deployed as-is |
| `app/core/config.py` | `secret_key = "change-me-in-production"` | Unsafe default |
| `frontend/src/app/router.tsx` | Hardcoded route map | Expected |
| `nav-config.ts` | Static nav items | Expected |
| `page-purpose.ts` | Static copy | Expected |
| Auth layout marketing copy | Static strings | Expected |

**No hardcoded business metrics** (scores, CVEs, repo counts) in production UI components.

---

## 15. Accessibility Problems

### Strengths

- `LoadingState` → `role="status"`, `aria-live="polite"`
- `ErrorState` → `role="alert"`
- Auth forms: `Label` + `htmlFor`, password toggle `aria-label`
- Sidebar `aria-label="Main navigation"`
- Table headers `scope="col"`
- Global `:focus-visible` ring
- `prefers-reduced-motion` in CSS

### Issues

| Issue | Location | WCAG impact |
|-------|----------|-------------|
| Decorative search implies ⌘K shortcut | `topbar.tsx` | Misleading affordance |
| Mobile drawer: no focus trap, no `aria-modal` | `sidebar.tsx`, `app-shell.tsx` | Keyboard/screen reader |
| Signup terms checkbox not linked to label | `signup-page.tsx` | Form labels |
| User avatar initials without accessible name | `topbar.tsx` | Name, role, value |
| Expand buttons lack finding-specific labels | `security-findings-table.tsx` | Button purpose |
| Nested `EmptyState` uses `<h2>` under page `<h1>` | Multiple pages | Heading order |
| Disabled settings controls rely on `title` only | `settings-pages.tsx` | Status communication |
| 404 uses `<a href>` not router `Link` | `router.tsx` | SPA navigation |
| No skip link to main content | `app-shell.tsx` | Bypass blocks |
| Charts absent — N/A for now | — | — |

---

## 16. Responsive Problems

### Works reasonably

- App shell: sidebar drawer below `md`, content `md:pl-60`
- `PageHeader` stacks on small screens
- `DataList` rows: mobile inline labels (`md:hidden` prefixes) on repos + PRs
- `DataTable`: horizontal scroll with `min-w-[640px]`
- Auth: marketing panel hidden below `lg`

### Problems

| Issue | Breakpoints affected |
|-------|---------------------|
| Sidebar opens without transition | All mobile |
| Topbar search hidden below `sm` — no mobile search alternative | <640px |
| Settings horizontal nav may clip without scroll affordance | Mobile/tablet |
| Tables require horizontal scroll (no card degradation) | <768px |
| Sign out hidden when user name block hidden | <640px |
| Repository detail metric grid may feel cramped | 320–390px |
| No verified testing at 320/375/390/1440/1920 | All |

---

## 17. UX Problems

1. **No first-run story** — signup → dashboard with empty metrics; onboarding skippable
2. **Dead analyze CTAs** erode trust across the product
3. **Workspace-wide security/quality pages** break mental model from repository detail
4. **PR page stops at risk score** — no file list, no findings in changed files
5. ~~**Analytics page underdelivers** on “engineering intelligence” promise~~ **Improved (Tier 8)** — historical trends, comparisons, regressions/improvements from real snapshots
6. **Notifications always empty** — bell icon promises activity that doesn't exist
7. **Settings feel scaffolded** — many disabled controls
8. **No metric definitions** — scores shown without “what does this mean?”
9. **No “attention required” unified inbox** — dashboard has pieces but no single triage view
10. **Forgot password false success** — user not told email isn't implemented

---

## 18. UI Consistency Problems

| Area | Issue |
|------|-------|
| Page layout | Same card+table template everywhere; weak visual hierarchy |
| Buttons | Primary actions inconsistent — some pages link to repos, others inert button |
| Empty states | Mix of `EmptyState`, inline text, table-internal empty |
| Typography | 13px base consistent; section titles vary (`CardTitle` vs plain `h2`) |
| Badges | Risk tones consistent via `risk-tone.ts` |
| Logo | Generic monogram; favicon still Vite default |
| Auth vs app shell | Auth has split panel; app is utilitarian — intentional gap but not premium |
| shadcn adoption | Partial — many patterns hand-rolled that shadcn tabs/dialog would standardize |

---

## 19. API Problems

| Issue | Details |
|-------|---------|
| No pagination | List endpoints return full org collections |
| No filtering/sorting params | Repos, findings, PRs filtered client-side or not at all |
| `isUnavailable` swallows 404/5xx as empty success | Frontend `use-async-data.ts` — can hide real errors |
| Analytics `range` / date filters | **Resolved (Tier 8)** | `GET /analytics/overview?from=&to=&repositoryId=`; legacy `/analytics` derives trend from snapshots |
| Quality summary unused fields | `averageComplexity`, etc. in schema, not computed |
| PR ID = GitHub ID | Consistent but undocumented; can confuse |
| No OpenAPI client generation | Manual `types/api.ts` sync risk |
| Cookie name config ignored | Settings vs implementation drift |
| No API versioning beyond `/v1` prefix | Fine for now |
| Finding status update API missing | Schema has statuses, no PATCH endpoint |

---

## 20. Database / Configuration Problems

| Issue | Details |
|-------|---------|
| MongoDB no auth in compose | Dev OK; prod risk |
| Redis no password in compose | Dev OK; prod risk |
| `/health` doesn't check Mongo/Redis | False positive health |
| No connection pool tuning | Motor defaults only |
| Findings not historical at item level | Snapshot aggregates only; per-finding history not stored |
| `webhook_deliveries` unbounded growth | No TTL index |
| Encryption key derived from `SECRET_KEY` | Rotating secret breaks GitHub tokens |
| `product-spec.md` references PostgreSQL | Docs out of sync with MongoDB |
| `.gitignore` missing `.venv/`, `cookies.txt` | Hygiene risk |
| No git repository initialized | No version control at audit time |
| Worker missing `LLM_*`, `CORS_*`, `FRONTEND_URL` in compose | Incomplete worker env |

**Recently fixed:** Invalid `create_index("_id", unique=True)` on `webhook_deliveries` — removed; indexes moved to `app/core/indexes.py`.

---

## 21. Security Problems

| Issue | Severity | Status |
|-------|----------|--------|
| Default `SECRET_KEY` | High | Must override in production |
| Webhook verification optional when secret empty | High | Must require secret in prod |
| RBAC not enforced | Medium | All members have full write |
| No rate limiting on auth/webhooks/AI | Medium | Abuse vector |
| No refresh token rotation/revocation | Medium | Stolen refresh persists |
| `DEBUG=true` in docker-compose | Medium | Insecure cookies |
| CORS `allow_methods/headers=["*"]` with credentials | Low | Review for production |
| OAuth errors in redirect URL | Low | Information leakage |
| No audit logging | Low | Compliance gap |
| No structured logging | Low | Incident response gap |
| Passwords correctly hashed | — | ✅ Good |
| GitHub tokens encrypted at rest | — | ✅ Good |
| Tenant isolation on queries | — | ✅ Good |
| AI prompts constrain hallucination | — | ✅ Good |

**No SOC 2 / ISO claims in production UI** — aligned with rules.

---

## 22. Performance Problems

| Area | Issue |
|------|-------|
| Full collection loads | No pagination on findings, PRs, dependencies |
| Dashboard | Aggregates in service; PR sort in memory |
| Analysis | Full git clone every run; no incremental |
| Frontend | No route-based code splitting |
| Frontend | Whole-page spinners; `MetricCard` skeleton unused |
| Celery | No job deduplication — duplicate analyze requests queue multiple runs |
| Docker image | Large (Node + Python + semgrep); no multi-stage |
| ESLint | `npx --yes` on every analysis — network latency |

---

## 23. Testing Gaps

### Backend (`backend/tests/` — 34 tests at audit time)

| File | What it tests | Real vs mock |
|------|---------------|--------------|
| `test_auth.py` | Signup, login, refresh, logout, me | Real MongoDB |
| `test_github.py` | OAuth callback, webhooks, repo connect | GitHub API mocked; DB real |
| `test_analysis_engine.py` | Parser fixtures, repo risk engine | Fixture JSON only |
| `test_pr_risk_engine.py` | PR risk factors | Pure unit |
| `test_finding_ai.py` | AI explain persistence | Fake LLM; real MongoDB |
| `test_dashboard.py` | Dashboard aggregation | Direct DB inserts |
| `test_analytics.py` | Analytics snapshot | Direct DB inserts |
| `test_indexes.py` | Index init, webhook idempotency | Real MongoDB |

**Not tested:**

- Full analysis pipeline (git clone + real scanners)
- Celery worker execution
- Real GitHub API / real LLM API
- RBAC (none to test)
- Analyzer timeout/failure visibility
- Webhook worker end-to-end
- Pagination, rate limits
- Production config validation

### Frontend (`frontend/src/` — 7 tests)

| File | Coverage |
|------|----------|
| `authService.test.ts` | Signup + refresh fetch contracts |
| `use-auth.test.tsx` | Session hydration |
| `protected-route.test.tsx` | Auth guards |

**Not tested:** All feature pages, `useAsyncData`, tables, metric cards, integrations UI, onboarding, shell, accessibility, responsive layouts.

### Tests that provide false confidence

| Test | Why misleading |
|------|----------------|
| `test_analysis_engine.py` | Tests parsers on static fixtures — not live scanner integration or orchestrator failure handling |
| `test_github.py` with mocked GitHub | Hides real API contract drift, rate limits, pagination |
| `test_finding_ai.py` with `FakeLLMProvider` | Doesn't validate real LLM JSON parsing failures |
| `test_analytics.py` | Only asserts snapshot mirrors dashboard — doesn't catch missing historical implementation |
| Frontend auth tests | Don't test actual login forms, error UI, or cookie behavior in browser |
| No E2E tests | Critical path signup → connect → analyze → view findings untested |

---

## 24. Deployment Problems

| Gap | Impact |
|-----|--------|
| No GitHub Actions CI | Quality gates manual only |
| No frontend Dockerfile / compose service | Inconsistent deploy story |
| No production compose overlay | Dev secrets in default compose |
| No healthchecks in compose | Race on cold start |
| No restart policies | Services don't auto-recover |
| No volume mounts for dev hot-reload in containers | Slow iteration in Docker |
| Backend image includes `tests/` | Bloated production image |
| No non-root container user | Security baseline |
| No monitoring/alerting | Operations blind spot |
| No root README | Onboarding friction |
| No git repo | Version control missing |

---

## 25. Recommended Implementation Order

Prioritized milestones that preserve working backend logic and build toward the full vision without a rewrite.

### Tier 0 — Foundation (do first)

1. **Project hygiene** — init git, fix `.gitignore`, remove/ignore `cookies.txt`, root README, GitHub Actions CI
2. **Config hardening** — production settings validation, document all env vars, require webhook secret in prod
3. **Fix dead UX that erodes trust** — wire `AnalyzeRepositoryButton` to navigate/trigger analysis; remove or implement topbar search
4. **RBAC enforcement** — backend deps + frontend route guards for write actions

### Tier 1 — Premium core (high product value)

5. **Design system completion** (Phase 1) — tokens, elevation, semantic colors, shared patterns; not decorative CSS
6. **Application shell** (Phase 4) — command palette, mobile nav a11y, breadcrumbs, working quick actions
7. **Dashboard decision center** (Phase 5) — attention required, metric definitions, actionable items
8. **Repository experience** (Phase 6) — tabs on detail, repo-scoped findings, analysis history API + UI
9. **PR intelligence** (Phase 7) — changed files, PR findings, merge recommendation depth

### Tier 2 — Domain depth

10. **Security center** (Phase 8) — filters, finding detail, status workflow API
11. **Code quality** (Phase 9) — filters, trends from stored runs
12. **Dependencies** (Phase 10) — npm audit if implemented; honest scan status labels
13. **Analysis pipeline hardening** (Phase 12) — timeouts, failure visibility, idempotent jobs
14. **Risk engine v2** (Phase 13) — richer signals, boundary tests

### Tier 3 — Growth surfaces

15. ~~**Historical analytics** (Phase 11)~~ **Done (Tier 8)** — `analysis_snapshots`, overview API, analytics page rebuild
16. **Marketing site** (Phase 2) — public routes, no false compliance claims
17. **Premium auth** (Phase 3) — password reset for real, strength indicator, reset page
18. **AI expansion** (Phase 14) — PR summary, usage logging; still no invented findings

### Tier 4 — Production readiness

19. **Database** (Phase 16) — pagination, historical collections, TTL, index review
20. **Accessibility audit remediation** (Phase 18)
21. **Responsive verification** (Phase 19) — all breakpoints
22. **Performance** (Phase 20) — pagination, code splitting, skeleton per-card loading
23. **State completeness** (Phase 21) — every screen all states
24. **Test expansion** (Phase 23) — integration tests for analysis pipeline, E2E critical path
25. **Deployment** — frontend Docker, prod compose, healthchecks, monitoring

### Explicitly defer until dependencies exist

- ~~Trend charts before historical `analysis_runs` / metric snapshots are stored~~ **Unblocked (Tier 8)**
- Export/share reports before core workflows are complete
- User-configurable dashboard sections before base dashboard is stable
- npm lockfile analysis before scanner is implemented

---

## Appendix A — File Reference Index

```
d:\verion\Verion\
├── docker-compose.yml
├── .gitignore                    # gaps: .venv, cookies.txt
├── cookies.txt                   # empty; should not be tracked
├── docs/
│   ├── product-spec.md           # PostgreSQL references outdated
│   ├── design-audit.md
│   └── production-audit.md       # this document
├── design-reference/verion/      # visual reference only; mocked
├── backend/
│   ├── app/main.py
│   ├── app/core/indexes.py
│   ├── app/core/config.py
│   ├── app/api/
│   ├── app/services/
│   ├── app/repositories/
│   ├── app/analyzers/
│   ├── app/workers/
│   └── tests/                    # 8 test modules, 34 tests
└── frontend/
    ├── src/app/router.tsx
    ├── src/api/
    ├── src/features/
    ├── src/components/
    ├── src/styles/index.css
    └── src/types/api.ts
```

## Appendix B — Cursor Rules Summary

Six always-applied rules in `.cursor/rules/`:

- `version-core.mdc` — REAL DATA, no design-reference imports, stack definition
- `backend.mdc` — layered architecture, real scanners, async analysis
- `frontend.mdc` — API separation, no mocks in production
- `ui.mdc` — four states, accessibility, responsive
- `security.mdc` — secrets, webhooks, no false compliance
- `testing.mdc` — milestone verification gate (lint, typecheck, build, pytest)

---

## Audit Completion Statement

**Phase 0 is complete.** No application code was modified during this audit.

The repository contains a **coherent v1 engineering intelligence core** with real analysis, scoring, and API-backed UI. The path to a premium production product is **incremental hardening and UX depth** — not a rewrite. The highest-leverage next steps are trust fixes (dead buttons, RBAC, config), design system + shell polish, and repository/PR workflow depth.

**Do not proceed to Phase 1 implementation until explicitly instructed.**
