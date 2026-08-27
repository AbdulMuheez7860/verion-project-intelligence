# Verion Product Specification

**Version:** 1.0 (draft)  
**Status:** Target product definition  
**Audience:** Engineering, product, and design teams building Verion

---

## 1. Vision

Verion is a **software engineering intelligence platform** that helps engineering teams understand the risk, quality, and security of every code change before it reaches production.

Verion connects to source control (initially GitHub), continuously analyzes repositories and pull requests, and surfaces **explainable, actionable intelligence** — not vanity metrics. It combines deterministic analysis (static analysis, dependency scanning, coverage) with contextual AI assistance to help reviewers prioritize work and ship safer software.

### What Verion is

- A **change intelligence** system centered on pull requests and repository health
- A **unified findings layer** across security, quality, dependencies, and testing
- An **explainable risk engine** that scores changes and shows contributing factors
- A **team workspace** for engineering leaders, reviewers, and developers

### What Verion is not

- A replacement for GitHub, GitLab, or CI/CD pipelines
- A generic BI dashboard or DORA-metrics-only tool
- An autonomous merge bot (Verion informs decisions; humans remain in control)
- A code hosting platform

---

## 2. Goals and Success Criteria

### Primary goals

1. **Reduce production incidents** caused by preventable code issues (security flaws, untested changes, risky dependency updates)
2. **Accelerate code review** by prioritizing high-risk pull requests and surfacing findings with file-level context
3. **Improve engineering visibility** with honest health scores and trends across repositories
4. **Build trust** through explainable scores, deterministic findings separate from AI suggestions, and clear remediation guidance

### Success metrics (product-level)

| Metric | Target direction |
|--------|------------------|
| Time to first meaningful review action on high-risk PRs | Decrease |
| Percentage of PRs with documented risk context before merge | Increase |
| Mean time to remediate critical security findings | Decrease |
| User-reported trust in risk scores (survey) | ≥ 4/5 |
| Weekly active engineering users per connected org | Growth |
| False-positive rate on security findings (user-dismissed as FP) | < 15% |

---

## 3. Users and Personas

### Engineering Lead / EM

- Needs portfolio view of repository health and team delivery signals
- Uses dashboard, analytics, and attention feeds
- Configures policies and notification rules

### Senior Engineer / Reviewer

- Needs PR-level risk breakdown, findings, and AI context during review
- Uses pull request detail, security, and code quality views
- Marks findings resolved or dismissed

### Developer / PR Author

- Needs clear feedback on their changes before and during review
- Uses PR detail, repository overview, and notifications
- Connects repos and triggers analysis

### Security / Platform Engineer

- Needs vulnerability tracking, dependency risk, and audit visibility
- Uses security center, dependencies, and settings (integrations, audit)
- Requires SSO and compliance features at scale

### Org Admin

- Manages team membership, integrations, billing, and workspace settings
- Uses settings (team, integrations, security, billing)

---

## 4. Core Concepts

### Workspace (Organization)

A tenant boundary. All repositories, members, findings, and settings belong to one workspace. Users may belong to multiple workspaces.

### Repository

A connected source code repository synced from a VCS provider. Verion tracks health scores, analysis history, and associated pull requests.

### Pull Request (Change)

A unit of review. Verion computes a **risk score**, aggregates findings, and optionally generates an **AI review** with recommendations.

### Analysis Run

An execution of Verion's analysis pipeline against a repository or pull request. Produces findings, scores, and metadata. States: `queued`, `running`, `complete`, `failed`.

### Finding

A deterministic issue detected by analysis (security, quality, dependency, coverage). Has severity, location (file, line), status lifecycle, and remediation guidance.

### Risk Score

A 0–100 score with **explainable factors** (e.g., security findings +22, low coverage +12). Lower is better for PR risk; higher is better for health scores.

### AI Review

Supplementary contextual analysis distinct from deterministic findings. Always labeled, includes confidence, and never silently overrides static analysis.

### Notification

An event-driven alert delivered in-app (and optionally email/Slack) when configured thresholds are met.

---

## 5. System Architecture (Target)

This specification is **backend-agnostic at the UI layer** but assumes a **FastAPI** service as the system of record.

```
┌─────────────────┐     HTTPS/REST      ┌──────────────────────────┐
│  Web Client     │ ◄──────────────────► │  FastAPI API             │
│  (any framework)│     WebSocket/SSE    │  - Auth & RBAC           │
└─────────────────┘                      │  - CRUD & queries        │
                                         │  - Webhook receivers     │
                                         └───────────┬──────────────┘
                                                     │
                    ┌────────────────────────────────┼────────────────────────┐
                    │                                │                        │
              ┌─────▼─────┐                  ┌───────▼───────┐        ┌───────▼───────┐
              │ PostgreSQL │                  │  Job Queue    │        │  Object Store │
              │ (primary)  │                  │  (Redis/etc.) │        │  (artifacts)  │
              └───────────┘                  └───────┬───────┘        └───────────────┘
                                                     │
                                              ┌──────▼──────┐
                                              │  Analysis   │
                                              │  Workers    │
                                              └──────┬──────┘
                                                     │
                              ┌──────────────────────┼──────────────────────┐
                              │                      │                      │
                        ┌─────▼─────┐         ┌──────▼──────┐       ┌──────▼──────┐
                        │  GitHub   │         │  SAST/SCA   │       │  LLM        │
                        │  API      │         │  Tools      │       │  Provider   │
                        └───────────┘         └─────────────┘       └─────────────┘
```

### Architectural principles

1. **API-first** — all product capabilities exposed via documented REST (and selective real-time) APIs
2. **Async analysis** — long-running work via job queue; clients poll or subscribe to status
3. **Deterministic before AI** — findings from static tooling are source of truth; AI adds context
4. **Multi-tenant isolation** — strict workspace scoping on every query and webhook event
5. **Idempotent webhooks** — VCS events may duplicate; processing must be safe to retry
6. **Explainability** — every score stores factor breakdown at computation time

---

## 6. Functional Requirements

### 6.1 Authentication and Authorization

#### Authentication

- Email/password signup with email verification
- Password reset via secure, time-limited token
- OAuth login via GitHub (primary SSO path for developers)
- Session management via HTTP-only cookies or bearer tokens (JWT with refresh)
- Optional enterprise SSO (SAML/OIDC) on Business tier

#### Authorization (RBAC)

| Role | Capabilities |
|------|--------------|
| Owner | Full workspace control, billing, delete workspace |
| Admin | Manage integrations, members, policies |
| Member | View all data, trigger analysis, manage own findings |
| Viewer | Read-only access to dashboards and findings |

All API endpoints enforce workspace membership and role checks.

---

### 6.2 Onboarding

**Goal:** Connect first repository and see first analysis within 10 minutes.

#### Flow

1. **Account creation** — name, email, password, workspace name
2. **Connect GitHub** — OAuth with minimum required scopes; explain permissions clearly
3. **Select repositories** — list accessible repos; user selects which to connect
4. **Initial analysis** — queue full scan; show progress
5. **Dashboard** — land on dashboard with first health scores and any critical findings

#### Requirements

- Skippable steps with persistent "complete setup" prompt until finished
- Clear error states for insufficient GitHub permissions
- Support connecting additional repos post-onboarding

---

### 6.3 GitHub Integration

#### Capabilities

- OAuth app or GitHub App installation (prefer GitHub App for webhooks and fine-grained permissions)
- Repository discovery and selective connection
- Webhook subscription for: `push`, `pull_request`, `pull_request_review`, `release` (configurable)
- Sync pull request metadata: title, author, status, files changed, diff stats
- Link out to GitHub for diffs, comments, and merge actions (Verion does not host diffs initially)

#### Sync behavior

- Initial backfill: open PRs + default branch HEAD
- Incremental: webhook-driven with periodic reconciliation job
- Display sync status and last synced timestamp per repository

---

### 6.4 Repository Management

#### Repository list

Display for each connected repository:

- Name, owner/org, primary language
- Health score (0–100)
- Open PR count
- Security score summary
- Test coverage percentage
- Risk level (low / medium / high / critical)
- Analysis status and last analyzed timestamp

**Actions:** search, filter by language/risk/status, sort by health/name/last analyzed, connect new repository, disconnect repository.

#### Repository detail

**Tabs:** Overview, Pull Requests, Code Quality, Security, Dependencies, Activity, Analysis History, Settings

**Overview metrics:**

- Health, security, coverage, dependency health, current risk
- Trend sparklines (30/90 day configurable)
- Recent activity feed

**Actions:**

- Trigger manual re-analysis
- Open in GitHub
- Configure analysis scope (branches, paths to include/exclude)
- Set coverage target for repository

---

### 6.5 Pull Request Intelligence

#### Pull request list

Display:

- PR number, title, repository
- Author
- Risk score (0–100) with severity band
- Files changed count
- Changed-code coverage %
- Status (open, needs review, high risk, merged, closed)
- Created/updated timestamps

**Actions:** filter by status/risk/repo/author, search, configure review policy (org-level).

#### Pull request detail

**Sections:**

1. **Summary** — metadata, risk badge, status, link to GitHub
2. **Risk analysis** — total score + factor breakdown with weights and explanations
3. **Security** — findings affecting this PR
4. **Code quality** — maintainability/complexity findings in changed files
5. **Testing** — coverage delta on changed lines vs repository target
6. **Dependencies** — package changes and vulnerability impact
7. **AI review** — generated summary and prioritized suggestions (clearly labeled)
8. **Changed files** — file list with per-file signals (not full diff v1)
9. **Timeline** — analysis runs, score changes, finding status changes

**Finding actions (on PR or repo findings):**

- Mark resolved (with reason)
- Dismiss (false positive, won't fix, duplicate)
- Acknowledge
- Suppress (admin, with expiry optional)

**Risk score factors (illustrative):**

| Factor | Example contribution |
|--------|------------------------|
| Security findings | +5 to +30 per severity |
| Code complexity delta | +5 to +20 |
| Files changed | +5 to +15 |
| Low changed-code coverage | +5 to +25 |
| Dependency risk | +5 to +20 |
| Historical incident correlation | +0 to +15 (future) |

Scores and factors must be **persisted at computation time** for auditability.

---

### 6.6 Security

#### Security center (workspace-wide)

**Metrics:**

- Security score (0–100)
- Counts by severity: critical, high, medium, low
- Secrets detected count
- Open vs resolved trend

**Findings table:**

- Severity, title, CWE/CVE identifier, file, line, repository, first/last detected, status

**Capabilities:**

- Filter by severity, status, repository, CWE/CVE
- Sort and full-text search
- Bulk status update
- Export findings (CSV/JSON)

#### Detection sources (phased)

| Phase | Capability |
|-------|------------|
| v1 | SAST rules (auth, injection, crypto), dependency CVEs, secret patterns |
| v2 | Custom policy rules, license violations, IaC scanning |
| v3 | Runtime correlation (optional integration) |

---

### 6.7 Code Quality

#### Metrics

- Quality score (0–100)
- Maintainability index
- Average cyclomatic complexity
- Duplication percentage
- Estimated technical debt (hours)

#### Findings

- Rule ID, severity, file, line, category (complexity, duplication, maintainability, style)
- Status lifecycle same as security findings

#### Policies (future)

- Block merge if quality score below threshold (via GitHub status check integration)

---

### 6.8 Dependencies (Supply Chain)

#### Metrics

- Dependency health score
- Total direct + transitive package count
- Outdated count
- Vulnerable count
- Abandoned/unmaintained count

#### Package table

- Package name, current version, latest version, status, CVE if any, license, repository

#### Capabilities

- Filter by status, license, repository
- View dependency graph (v2)
- Trigger dependency-only re-scan

---

### 6.9 Analytics and Reporting

#### Workspace analytics

**Delivery metrics:**

- PR throughput (merged per period)
- Merge frequency
- Median time to first review
- Median time to merge
- Average PR size (files/lines)
- Average PR risk score
- Deployment-related risk proxy (% merges with post-merge findings)

**Quality/security trends:**

- Coverage, quality score, security score, risk score over time
- Per-repository and per-team breakdowns (v2)

#### Requirements

- Configurable date range (7d, 30d, 90d, custom)
- Comparison to previous period with % change
- Metric definitions accessible in UI (tooltip or glossary)
- Export report (PDF summary v2; CSV for metrics v1)

---

### 6.10 Dashboard

The dashboard is the **default authenticated landing page**.

#### Components

1. **Personalized greeting** with date and workspace name
2. **Top KPI cards** (5): repository health, PR risk, security score, code quality, test coverage — each with trend vs prior period
3. **Engineering health trend** — workspace-aggregated time series
4. **Attention needed** — prioritized actionable items with deep links
5. **Recent pull requests** — highest-risk or recently updated
6. **PR activity summary** — opened/merged/closed counts with trend

#### Attention feed rules (priority order)

1. Critical security findings (unresolved, < 24h)
2. High-risk open PRs without review
3. Coverage regression below repository target
4. Vulnerable dependency updates pending
5. Failed analysis runs

---

### 6.11 Notifications

#### Channels

- In-app notification center (v1)
- Email (v1 for critical)
- Slack/webhook (v2)

#### Event types

| Event | Default |
|-------|---------|
| Critical security finding | On |
| High-risk PR opened | On |
| Analysis completed | On |
| Dependency vulnerability detected | On |
| Weekly engineering summary | On |
| Analysis failed | On |

#### Requirements

- Per-user notification preferences
- Mark read/unread
- Deep link to relevant resource
- Batched digest for non-critical events
- Do not notify for dismissed/resolved findings

---

### 6.12 Settings

#### Profile

- Name, email, avatar, timezone
- Password change
- Connected OAuth accounts

#### Team

- Member list with roles
- Invite by email
- Remove member, change role
- Pending invitations

#### Integrations

- GitHub connection status, org, connected repo count
- Webhook health indicator
- Connect / reconnect / disconnect
- (v2) Slack, Jira, PagerDuty

#### Notifications

- Toggle per event type and channel

#### Security

- Active sessions list with revoke
- Sign out all sessions
- Two-factor authentication (v2)
- API tokens for automation (v2)
- Audit log viewer (Business tier)
- Delete account / delete workspace (owner, with confirmation)

#### Billing (when applicable)

- Current plan, usage (repos, AI review credits)
- Upgrade/downgrade
- Invoice history

---

### 6.13 Search and Command Palette

#### Global search

- Search repositories, pull requests, findings by title, ID, file path
- Keyboard shortcut: `⌘K` / `Ctrl+K`
- Recent items and quick navigation actions
- Results grouped by type with keyboard navigation

#### Requirements

- Sub-200ms response for typical workspaces (indexed)
- Respect RBAC — only return accessible resources

---

### 6.14 AI Review Credits (Commercial)

- Workspaces have a monthly AI review quota by plan
- Each AI review generation consumes one credit
- Display remaining credits in UI
- Graceful degradation when exhausted (deterministic findings still available)

---

### 6.15 Help and Documentation

- Searchable help center with guides: getting started, GitHub integration, risk scores, code quality, AI reviews, FAQ
- Contextual help links from metric cards
- Status page link for platform incidents

---

## 7. API Contract Overview (FastAPI)

All endpoints are workspace-scoped unless noted. Authentication required except public auth routes.

### Auth

```
POST   /api/v1/auth/signup
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
GET    /api/v1/auth/me
POST   /api/v1/auth/oauth/github
```

### Repositories

```
GET    /api/v1/repositories
POST   /api/v1/repositories              # connect
GET    /api/v1/repositories/{id}
DELETE /api/v1/repositories/{id}
POST   /api/v1/repositories/{id}/analyze
GET    /api/v1/repositories/{id}/analyses
GET    /api/v1/repositories/{id}/metrics
PATCH  /api/v1/repositories/{id}/settings
```

### Pull Requests

```
GET    /api/v1/pull-requests
GET    /api/v1/pull-requests/{id}
GET    /api/v1/pull-requests/{id}/risk
GET    /api/v1/pull-requests/{id}/findings
POST   /api/v1/pull-requests/{id}/ai-review
GET    /api/v1/pull-requests/{id}/timeline
```

### Findings

```
GET    /api/v1/findings                  # filters: type, severity, status, repo
PATCH  /api/v1/findings/{id}             # status update
```

### Domain-specific aggregates

```
GET    /api/v1/security/summary
GET    /api/v1/quality/summary
GET    /api/v1/dependencies
GET    /api/v1/analytics                 # ?range=30d
GET    /api/v1/dashboard
```

### Notifications

```
GET    /api/v1/notifications
PATCH  /api/v1/notifications/{id}/read
POST   /api/v1/notifications/read-all
GET    /api/v1/notification-preferences
PUT    /api/v1/notification-preferences
```

### Integrations

```
GET    /api/v1/integrations/github
POST   /api/v1/integrations/github/connect
DELETE /api/v1/integrations/github
POST   /api/v1/webhooks/github           # inbound, unsigned verification
```

### Team

```
GET    /api/v1/team/members
POST   /api/v1/team/invitations
DELETE /api/v1/team/members/{id}
PATCH  /api/v1/team/members/{id}
```

### Search

```
GET    /api/v1/search?q={query}&types=repo,pr,finding
```

### Real-time (optional v1.1)

```
WS     /api/v1/ws/notifications
SSE    /api/v1/analyses/{id}/stream
```

---

## 8. Data Model (Logical)

```
User
  ├── Membership → Organization (role)
  └── NotificationPreference

Organization (Workspace)
  ├── Integration (GitHub)
  ├── Repository
  │     ├── AnalysisRun
  │     ├── RepositorySettings
  │     └── PullRequest
  │           ├── RiskScore (+ factors[])
  │           ├── Finding[]
  │           └── AIReview
  ├── Finding (workspace-wide index)
  ├── AuditLog
  └── Subscription

Notification → User, resource reference
```

### Key enums

- `RiskLevel`: low | medium | high | critical
- `AnalysisStatus`: queued | running | complete | failed
- `FindingStatus`: open | acknowledged | false_positive | resolved | suppressed
- `PullRequestStatus`: open | merged | closed
- `IntegrationStatus`: not_connected | connecting | connected | syncing | error

---

## 9. Analysis Pipeline

### Trigger events

- Repository connected (full scan)
- Webhook: push to default branch (incremental)
- Webhook: pull request opened/synchronize
- Manual "Analyze now"
- Scheduled nightly reconciliation

### Pipeline stages

1. **Fetch** — clone or fetch diff via GitHub API
2. **Static security scan** — SAST rules, secret detection
3. **Dependency scan** — parse lockfiles, query advisory DB
4. **Quality scan** — complexity, duplication, lint rules
5. **Coverage ingest** — parse coverage report if CI uploads (or estimate from available data)
6. **Score computation** — aggregate into health/risk scores with factor breakdown
7. **AI review** (optional, if credits available) — contextual summary on PRs only
8. **Persist and notify** — store results, emit notifications for threshold breaches

### Failure handling

- Retry transient failures (3x with backoff)
- Mark analysis `failed` with error message
- Notify repo admins on repeated failures

---

## 10. Non-Functional Requirements

### Performance

| Operation | Target |
|-----------|--------|
| API read (list/detail) | p95 < 300ms |
| Dashboard load | p95 < 500ms |
| PR analysis (median repo) | < 3 minutes |
| Search | p95 < 200ms |
| Webhook processing ack | < 5s (async processing) |

### Reliability

- 99.9% API availability (production)
- Analysis job durability — no lost jobs on worker restart
- Database backups daily with point-in-time recovery

### Security

- TLS everywhere
- Encrypted secrets at rest
- OWASP ASVS Level 2 alignment for auth flows
- Rate limiting on auth and webhook endpoints
- GitHub webhook signature verification
- Tenant isolation audits
- SOC 2 Type II target (Business tier claim)

### Scalability

- Horizontal scaling of API and workers
- Per-workspace rate limits on analysis triggers
- Archive old analysis runs per retention policy

### Observability

- Structured logging with correlation IDs
- Metrics: analysis duration, queue depth, error rates
- Tracing across webhook → job → API

---

## 11. UX and Design Requirements

These requirements describe **product UX expectations**. Visual implementation should follow the design reference tone system but is not bound to the v0 component structure.

### Information architecture

```
Marketing site
  └── Auth flows
        └── Onboarding
              └── App
                    ├── Dashboard
                    ├── Repositories → Detail
                    ├── Pull Requests → Detail
                    ├── Code Quality
                    ├── Security
                    ├── Dependencies
                    ├── Analytics
                    ├── Settings (profile, team, integrations, notifications, security)
                    └── Help
```

### Visual language

- **Tone colors:** healthy (green), warning (amber), critical (red), neutral (gray)
- **Scores:** monospace numerals with semantic color
- **Cards:** bordered, subtle shadow, rounded corners
- **Primary brand:** indigo/violet accent (adjustable via design tokens)
- **Dark mode:** full support, user preference persisted

### Responsive

- Mobile: collapsible navigation, stacked data rows with labels
- Tablet: sidebar visible, condensed tables
- Desktop: full multi-column layouts, 5-up metric grids

### Accessibility (WCAG 2.1 AA target)

- Keyboard navigable command palette with focus trap
- Visible focus indicators
- Chart alternatives (data table or aria labels)
- Color not sole indicator of status
- Screen reader labels on icon-only controls
- Reduced motion support

---

## 12. Pricing Tiers (Product)

| Capability | Free | Team | Business |
|------------|------|------|----------|
| Repositories | 2 | Unlimited | Unlimited |
| Risk analysis | Basic | Full | Full + custom weights |
| AI review credits | 50/mo | 1,000/mo | Custom |
| History retention | 7 days | 90 days | 1 year+ |
| SSO | — | — | SAML/OIDC |
| Audit logs | — | — | Yes |
| Custom policies | — | — | Yes |
| Support | Community | Email | Priority |

---

## 13. Release Phases

### Phase 1 — Foundation (MVP)

- Auth (email + GitHub OAuth)
- GitHub integration (connect repos, webhooks)
- Repository list and detail (overview only)
- PR list and detail (risk score, deterministic findings)
- Security and quality findings tables
- Dashboard with KPIs and attention feed
- Basic notifications (in-app)
- Analysis pipeline v1 (SAST + dependencies + basic quality)
- FastAPI backend with PostgreSQL

### Phase 2 — Depth

- AI review with credit system
- Analytics page with trends and export
- Dependency center with full package table
- Settings (team, integrations, notification prefs)
- Command palette with search
- Email notifications
- PR timeline and finding lifecycle actions

### Phase 3 — Scale

- SSO and audit logs
- Custom risk weights and policies
- GitHub status checks / merge gate integration
- Slack integration
- Coverage report CI upload
- Per-team analytics
- Billing and self-serve upgrade

---

## 14. Out of Scope (v1)

- GitLab/Bitbucket support
- Full inline code diff viewer
- Auto-merge or auto-approve
- IDE plugins
- Self-hosted deployment (evaluate for Business later)
- Custom SAST rule authoring UI
- Runtime/application security (RASP)

---

## 15. Open Questions

1. **GitHub App vs OAuth App** — finalize based on webhook and permission requirements
2. **Coverage without CI integration** — clarify MVP behavior when no coverage uploaded
3. **AI provider** — selection, data residency, and whether code leaves tenant boundary
4. **Finding deduplication** — rules for same issue across commits
5. **Multi-workspace UX** — workspace switcher in shell
6. **Data retention** — hard delete vs archive on repo disconnect

---

## 16. Glossary

| Term | Definition |
|------|------------|
| Changed-code coverage | Test coverage percentage on lines modified in a PR |
| Deterministic finding | Issue from static tooling with reproducible evidence |
| Health score | Repository-level 0–100 composite of quality, security, coverage, dependencies |
| Risk score | PR-level 0–100 score indicating merge risk (higher = riskier) |
| Workspace | Top-level organizational tenant in Verion |
| Analysis run | Single execution of the analysis pipeline |

---

## Appendix: v0 Reference Mapping

The v0 design reference (`design-reference/verion/`) informed visual patterns documented in `docs/design-audit.md`. This product specification intentionally **does not** adopt the v0 technical architecture (monolithic client component, localStorage auth, inline mocks). Use the audit for UX inventory; use this document for what to build.

| v0 pattern | Production equivalent |
|------------|----------------------|
| `MetricCard` + sparkline | Dashboard API + chart component with real time series |
| `DataPage` template | Separate pages sharing layout; data from `/security`, `/quality`, etc. |
| `demoAuthAdapter` | FastAPI auth with secure sessions |
| `lib/mock` data | PostgreSQL + analysis workers |
| Decorative `MiniChart` | Data-driven charts from analytics API |
| Command palette (nav only) | Search API with indexed resources |
| Dual PR detail components | Single PR detail view per spec section 6.5 |
