# Verion v0 Design Reference Audit

**Source:** `design-reference/verion/` (user-specified path `design-reference/verion-v0/` — not present; audit covers the available reference at `design-reference/verion/`)

**Purpose:** Exhaustive inventory of the v0 visual prototype. This document describes what exists in the reference implementation only. It does **not** prescribe production architecture.

**Audit date:** August 12, 2026

---

## Executive Summary

The v0 reference is a **Next.js 16 App Router** frontend prototype with:

- **57 files**, predominantly UI and routing scaffolding
- **All domain data mocked** in `lib/mock/index.ts` or hardcoded inline in `components/verion-app.tsx`
- **Demo authentication** via `localStorage` (`demo-auth-adapter.ts`)
- **Service layer stubs** in `lib/api/services.ts` that fall back to mocks when `NEXT_PUBLIC_API_URL` is unset
- **No real backend**, no database, no GitHub OAuth, no analysis engine
- **Two parallel UI implementations** for some views: a rich inline prototype in `verion-app.tsx` (used by most pages) and thinner "production-shaped" components for repository/PR detail and settings sub-pages

The reference is valuable for **visual language, information architecture, and UX patterns** — not for system design.

---

## 1. Every Page

### Public / Marketing

| Page | Route | Component | Notes |
|------|-------|-----------|-------|
| Landing | `/` | `Landing` in `verion-app.tsx` | Full marketing page with hero, features, security, pricing |
| Features | `/features` | `PublicLanding` → same `Landing` | Anchor-only; renders full landing |
| Pricing | `/pricing` | `PublicLanding` → same `Landing` | Anchor-only; renders full landing |
| Security (marketing) | `/security` | `PublicLanding` → same `Landing` | Anchor-only; renders full landing |
| About | `/about` | `PublicLanding` → same `Landing` | Anchor-only; renders full landing |

### Authentication

| Page | Route | Component | Notes |
|------|-------|-----------|-------|
| Login | `/login` | `AuthForm` (`auth-forms.tsx`) | Demo auth with validation |
| Sign up | `/signup` | `AuthForm` | Creates localStorage session |
| Forgot password | `/forgot-password` | `AuthForm` | Fake email flow |
| Reset password | `/reset-password` | `AuthForm` | Fake reset flow |

### Onboarding

| Page | Route | Component | Notes |
|------|-------|-----------|-------|
| Onboarding wizard | `/onboarding` | `Onboarding` in `verion-app.tsx` | 3-step wizard, skippable |

### Application (authenticated shell)

| Page | Route | Component | Notes |
|------|-------|-----------|-------|
| App index | `/app` | Redirect | → `/app/dashboard` |
| Dashboard | `/app/dashboard` | `Dashboard` | Default app home |
| Repositories list | `/app/repositories` | `Repositories` | Searchable table |
| Repository detail | `/app/repositories/[id]` | `RepositoryDetail` | Separate, simpler component |
| Pull requests list | `/app/pull-requests` | `PullRequests` | Filterable table |
| Pull request detail | `/app/pull-requests/[id]` | `PullRequestDetail` OR `PRDetail` | **Dual implementation** — Next route uses thinner `PullRequestDetail`; `verion-app.tsx` has richer `PRDetail` unused by App Router |
| Code quality | `/app/code-quality` | `DataPage kind="quality"` | Shared data page template |
| Security center | `/app/security` | `DataPage kind="security"` | Shared data page template |
| Dependencies | `/app/dependencies` | `DataPage kind="dependencies"` | Shared data page template |
| Analytics | `/app/analytics` | `DataPage kind="analytics"` | Shared data page template |
| Settings (profile) | `/app/settings` | `Settings` | Inline profile form only |
| Settings profile | `/app/settings/profile` | `SettingsSection section="profile"` | Separate sub-page |
| Settings team | `/app/settings/team` | `SettingsSection section="team"` | |
| Settings integrations | `/app/settings/integrations` | `SettingsSection section="integrations"` | |
| Settings notifications | `/app/settings/notifications` | `SettingsSection section="notifications"` | |
| Settings security | `/app/settings/security` | `SettingsSection section="security"` | |
| Help center | `/app/help` | `Help` | Card grid of guides |

### System Pages

| Page | Route | Component | Notes |
|------|-------|-----------|-------|
| App loading | `/app/*` (suspense) | `app/app/loading.tsx` | Generic loading state |
| App error | `/app/*` (error boundary) | `app/app/error.tsx` | Retry button |
| 404 | unmatched | `app/not-found.tsx` | Link home |

---

## 2. Every Route

```
/                           → Landing
/features                   → Landing (anchor)
/pricing                    → Landing (anchor)
/security                   → Landing (anchor)
/about                      → Landing (anchor)
/login                      → AuthForm (login)
/signup                     → AuthForm (signup)
/forgot-password            → AuthForm (forgot)
/reset-password             → AuthForm (reset)
/onboarding                 → Onboarding wizard

/app                        → redirect /app/dashboard
/app/dashboard              → Dashboard
/app/repositories           → Repositories list
/app/repositories/:id       → RepositoryDetail
/app/pull-requests          → PullRequests list
/app/pull-requests/:id      → PullRequestDetail
/app/code-quality           → DataPage (quality)
/app/security               → DataPage (security)
/app/dependencies           → DataPage (dependencies)
/app/analytics              → DataPage (analytics)
/app/settings               → Settings (profile inline)
/app/settings/profile       → SettingsSection (profile)
/app/settings/team          → SettingsSection (team)
/app/settings/integrations  → SettingsSection (integrations)
/app/settings/notifications → SettingsSection (notifications)
/app/settings/security      → SettingsSection (security)
/app/help                   → Help
```

**Query parameters used:** `?next=` on login redirect from `ProtectedGate` (preserves intended destination).

**No API routes** defined in the Next.js app — all API calls target external `NEXT_PUBLIC_API_URL`.

---

## 3. Every Navigation Item

### Marketing header (`Landing`)

- Features (`#features`)
- Security (`#security`)
- Pricing (`#pricing`)
- About (`#about`)
- Sign in → `/login`
- Start free → `/signup`

### Marketing footer

- Same anchor links + © 2026 Verion

### App sidebar — primary (`nav` array)

| Label | Route | Icon | Badge |
|-------|-------|------|-------|
| Dashboard | `/app/dashboard` | LayoutDashboard | — |
| Repositories | `/app/repositories` | Box | — |
| Pull Requests | `/app/pull-requests` | GitPullRequest | **12** (hardcoded) |
| Code Quality | `/app/code-quality` | Code2 | — |
| Security | `/app/security` | ShieldCheck | **3** (hardcoded) |
| Dependencies | `/app/dependencies` | Package | — |
| Analytics | `/app/analytics` | LineChart | — |

### App sidebar — bottom (`bottomNav`)

| Label | Route | Icon |
|-------|-------|------|
| Settings | `/app/settings` | Settings |
| Help center | `/app/help` | CircleHelp |

### Workspace switcher (sidebar)

- "Acme Platform" / "Engineering" — **non-functional** dropdown button

### Repository detail tabs (non-functional)

Overview, Pull Requests, Code Quality, Security, Dependencies, Activity, Analysis History, Settings

### PR detail tabs (in rich `PRDetail` — non-functional)

Summary, Risk analysis, Security, Code quality, Testing, Dependencies, AI review, Changed files, Timeline

### Settings sub-nav (in `Settings` component — partially wired)

Profile, Team, Integrations, Notifications, Security — only Integrations navigates to `/app/settings/integrations`

### Command palette navigation items

First 5 primary nav items (Dashboard through Security)

---

## 4. Every Major UI Component

### Shell & Layout

| Component | Location | Purpose |
|-----------|----------|---------|
| `AppShell` | `verion-app.tsx` | Sidebar + topbar + main content wrapper |
| `Sidebar` | `verion-app.tsx` | Fixed left nav, mobile overlay |
| `Topbar` | `verion-app.tsx` | Search trigger, theme toggle, notifications, user menu |
| `Logo` | `verion-app.tsx` | "V" mark + VERION wordmark |
| `PageHeader` | `verion-app.tsx` | Eyebrow, title, description, optional action |
| `ProtectedGate` | `route-views.tsx` | Auth guard redirecting to `/login?next=` |
| `CommandPalette` | `verion-app.tsx` | Modal search/navigation overlay |

### Data Display

| Component | Location | Purpose |
|-----------|----------|---------|
| `MetricCard` | `verion-app.tsx` | KPI card with mini chart |
| `MiniChart` | `verion-app.tsx` | SVG line chart or CSS bar chart (decorative) |
| `Badge` | `verion-app.tsx` | Status pill with `StatusDot` |
| `Score` | `verion-app.tsx` | Colored numeric score |
| `StatusDot` | `verion-app.tsx` | healthy/warning/critical/neutral indicator |
| `MiniInfo` | `verion-app.tsx` | Small summary card (PR detail) |
| `DataPage` | `verion-app.tsx` | Reusable page for quality/security/deps/analytics |

### Page Views

| Component | Location |
|-----------|----------|
| `Landing` | `verion-app.tsx` |
| `Dashboard` | `verion-app.tsx` |
| `Repositories` | `verion-app.tsx` |
| `PullRequests` | `verion-app.tsx` |
| `PRDetail` | `verion-app.tsx` (rich, unused by App Router) |
| `PullRequestDetail` | `pull-requests/pr-detail.tsx` (used by App Router) |
| `RepositoryDetail` | `repositories/repository-detail.tsx` |
| `Settings` | `verion-app.tsx` |
| `SettingsSection` | `settings/settings-sections.tsx` |
| `Help` | `verion-app.tsx` |
| `Onboarding` | `verion-app.tsx` |
| `AuthPage` | `verion-app.tsx` (legacy, unused) |
| `AuthForm` | `auth/auth-forms.tsx` (used) |

### State Components

| Component | Location |
|-----------|----------|
| `LoadingState` | `states.tsx` |
| `EmptyState` | `states.tsx` |
| `ErrorState` | `states.tsx` |

### UI Primitives

| Component | Location | Usage in v0 |
|-----------|----------|-------------|
| `Button` | `components/ui/button.tsx` | Defined but **not used** — all buttons are raw `<button>` elements |

---

## 5. Every Dashboard Metric

### Top-row KPI cards (`Dashboard`)

| Metric | Value (mock) | Trend | Detail |
|--------|--------------|-------|--------|
| Repository health | 86 / 100 | ↑ 8.4% | vs previous 30 days · Healthy |
| PR risk | 32 / 100 | ↓ 12.1% | Average risk score · Low |
| Security score | 91 / 100 | ↑ 4.2% | 3 open findings · Good |
| Code quality | 87 / 100 | ↑ 5.8% | Maintainability index · Good |
| Test coverage | 78.6% | ↑ 2.4% | Changed code · Needs focus |

### Engineering health trend section

- Combined health score line chart (68 → 86 over Jul 14 – Aug 12)
- X-axis labels: Jul 14, Jul 21, Jul 28, Aug 4, Aug 12

### Attention needed panel

| Signal | Meta |
|--------|------|
| Critical vulnerability in customer-portal | CVE-2026-2847 · 18 min ago |
| PR #142 has elevated risk | payment-service · 2 hours ago |
| Coverage dropped below target | identity-platform · 76% |
| 7 dependencies need updates | Across 3 repositories |

### Recent pull requests (top 3)

- Risk scores per PR from `pullRequests` array

### Pull request activity

- Opened: 48, Merged: 36, Closed: 7
- Trend badge: +18.2%
- Bar chart (decorative)

### Sidebar AI credits widget

- 750 of 1,000 reviews left (75% progress bar)

### Greeting header

- "Good morning, Alex"
- Date eyebrow: "Monday, August 12, 2026"

---

## 6. Every Chart

| Chart | Location | Type | Data Source |
|-------|----------|------|-------------|
| MetricCard mini line | Dashboard KPIs | SVG path | Hardcoded curve |
| MetricCard mini bars | Security/coverage KPIs | CSS div bars | Hardcoded heights `[44,62,38,70,55,82,65,90,72,78,88,94]` |
| Engineering health trend | Dashboard main | SVG area + line | Hardcoded path, grid lines |
| PR activity | Dashboard | MiniChart bars (cyan) | Hardcoded |
| DataPage trend | Quality/Security/Deps/Analytics | MiniChart line | Hardcoded, color varies by `kind` |
| DataPage breakdown | Secondary panel | CSS bar chart | Hardcoded heights `[42,68,28,55,36]` |
| Landing hero preview | Marketing | MiniCharts | Hardcoded |
| PR risk factor bars | PRDetail (rich) | Progress bars | Hardcoded widths `[88,62,48,58,37]` |

**No charting library** (Recharts, Chart.js, etc.) — all SVG/CSS decorative.

---

## 7. Every Table

### Repositories list (responsive grid/table hybrid)

| Column | Sample values |
|--------|---------------|
| Repository | name, owner, language |
| Health | 86, 74, 91, 62 |
| Open PRs | 4, 7, 2, 9 |
| Security | A, B, A, C (badge) |
| Coverage | 82%, 76%, 89%, 64% |
| Risk | Low, Medium, Low, High |
| Last analysis | relative timestamps |

### Pull requests list

| Column | Sample values |
|--------|---------------|
| Pull request | #id + title, repo |
| Author | avatar initials + name |
| Risk | 72, 48, 31, 64 |
| Files | 18, 9, 6, 22 |
| Coverage | 58%, 91%, 86%, 67% |
| Status | Needs review, Open |
| Created | relative timestamps |

### DataPage findings/metrics table (varies by `kind`)

**Code quality columns:** Severity, Rule, File, Line, Category, Status

**Security columns:** Severity, Finding, CWE, File, Line, Status

**Dependencies columns:** Package, Current, Latest, Status, Vulnerability, License

**Analytics columns:** Metric, Current period, Previous period, Change, Definition

Each has 3 hardcoded rows.

### Settings team section

Member name + role list (not a formal table).

---

## 8. Every Modal / Dialog

| Modal | Trigger | Behavior |
|-------|---------|----------|
| **Command palette** | ⌘K button, search icon (mobile), `onCommand` | Full-screen overlay; navigate to 5 routes; ESC hint; click outside closes |
| **Mobile sidebar overlay** | Hamburger menu | Backdrop + slide-in sidebar |
| **Auth success screen** | Form submit (forgot/reset) | Centered card, not true modal |

**No other modals:** no confirmation dialogs, no notification drawer, no org switcher dropdown, no filter popovers (filter buttons are non-functional).

---

## 9. Every Form

### Auth forms (`AuthForm`)

| Form | Fields | Validation |
|------|--------|------------|
| Login | Email, Password | Email regex, password ≥8 chars |
| Signup | Full name, Company/team, Email, Password, Confirm password, Terms checkbox | All required, passwords match, terms accepted |
| Forgot password | Email | Email regex |
| Reset password | Password, Confirm password | ≥8 chars, match |

**Actions:** Sign in, Create workspace, Send reset link, Reset password, Continue with GitHub (non-functional), password visibility toggle.

### Settings profile (`Settings` + `SettingsSection`)

- Full name, Timezone (select), Email address
- Save changes → local `saved` state only

### Settings notifications

- 5 checkboxes (default checked): Security alerts, Critical PR alerts, Analysis complete, Dependency vulnerabilities, Weekly report

### Settings security

- Review buttons (non-functional) for: Password and sessions, Connected accounts, Active sessions, Sign out all sessions
- Delete account button (non-functional)

### Search inputs (filter only, no submit)

- Repositories search
- Pull requests search
- Help center search
- Command palette search (no filtering logic)

### Onboarding

- No data entry — step navigation only

---

## 10. Every User Interaction

| Interaction | Location | Functional? |
|-------------|----------|-------------|
| Navigate via sidebar | App shell | ✅ Client-side routing |
| Navigate via command palette | Topbar | ✅ 5 routes only |
| Toggle dark/light theme | Topbar | ✅ Toggles `.dark` on `<html>` |
| Open/close mobile menu | Topbar/Sidebar | ✅ |
| Search repositories | Repositories | ✅ Client-side filter by name |
| PR list filters (All/Open/Needs review/High risk) | Pull requests | ❌ Visual only — no state change |
| PR/repo search | Lists | ❌ Input present, PR search not wired |
| Sort/filter repos (language, health) | Repositories | ❌ Buttons non-functional |
| Date range selector (30 days) | Dashboard, DataPages | ❌ Non-functional |
| Connect GitHub / Connect repository | Multiple | ❌ No action |
| Export report | DataPages | ❌ No action |
| Configure review policy | Pull requests | ❌ No action |
| Analyze now | Repository detail | ❌ No action |
| GitHub external link | Repository detail | ❌ No href |
| Mark resolved / Dismiss AI finding | PRDetail | ❌ No action |
| Notification bell | Topbar | ❌ No dropdown |
| User menu (ChevronDown) | Topbar | ❌ No dropdown |
| Org/workspace switcher | Sidebar | ❌ No dropdown |
| Help guide cards | Help | ❌ No navigation |
| Landing anchor links | Marketing | ✅ Scroll to section |
| View demo | Landing | ✅ → `/app/dashboard` (unauthenticated unless gated) |
| Pricing CTAs | Landing | ✅ → `/signup` or `/about` |
| Auth form submit | Auth pages | ✅ Demo localStorage auth |
| GitHub OAuth button | Login | ❌ No OAuth |
| Onboarding steps | Onboarding | ✅ Step state; skip → dashboard |
| Save settings | Settings | ✅ Local toast only |
| Back navigation | Detail pages | ✅ `history.back()` |
| Error retry | Error boundary | ✅ `reset()` |
| Metric help (?) buttons | MetricCard | ❌ No tooltip/modal |
| More options (⋯) | Various | ❌ No menu |

---

## 11. Repository-Related Features

### Implemented (visual/mock)

- Repository list with health, PR count, security grade, coverage, risk, last analysis
- Client-side name search
- Repository detail page with:
  - Overview metrics: Health, Security, Coverage, Dependency health (derived), Current risk (derived)
  - Tab bar (8 tabs, non-functional)
  - Analysis history list (3 hardcoded events)
  - Repository context blurb
  - "Analyze now" and "GitHub" buttons
- Connect repository CTA on dashboard and repositories page
- Mock data model: `Repository` type with `analysisStatus` (not_started | queued | running | complete | failed)
- `repositoryService.get/list` with mock fallback
- `analysisService.start` stub endpoint

### Not implemented

- Real GitHub connection or repo sync
- Webhook ingestion
- Analysis job queue/progress
- Repo settings
- Branch protection integration
- Historical trend per repo
- Repo-level filtering by language/org

---

## 12. Pull-Request Features

### Implemented (visual/mock)

- PR list with risk score, files changed, coverage, status, author
- Filter chips (visual only)
- PR detail (App Router version): status, coverage, findings count, risk badge
- PR detail (rich `PRDetail` in verion-app — not routed):
  - Risk analysis breakdown (5 factors with contributions)
  - AI review section with findings, confidence, file:line, actions
  - Summary cards: Security, Testing, Changed files
  - 9-tab navigation (non-functional)
- Mock `PullRequest` and `RiskScore` types
- `pullRequestService.get/list` with mock fallback
- Dashboard recent PRs widget
- Attention-needed PR signal

### Not implemented

- Real GitHub PR sync
- Diff/file viewer
- Review comments
- Merge/block policies
- Risk score computation
- AI review generation
- Mark resolved/dismiss workflows
- Timeline/events
- PR comparison across repos

---

## 13. Security Features

### Product surface (visual)

- Security center page (`DataPage kind="security"`)
- Security score metric (dashboard + repo)
- Security findings table: Severity, Finding, CWE, File, Line, Status
- Severity breakdown chart
- Metrics: Security score, Critical, High, Medium, Secrets counts
- PR security tab and findings in rich PR detail
- Marketing security section
- Settings → Security: sessions, connected accounts, danger zone
- Notification type: Security alerts
- Sidebar badge: 3 open (hardcoded)

### Mock data examples

- CWE-862 Missing authorization check
- CWE-614 Weak session cookie flags
- CWE-1104 Outdated crypto library
- CVE-2026-2847 (dashboard attention item)

### Not implemented

- SAST/secret scanning engines
- CVE database lookups
- Finding lifecycle (acknowledge, suppress, resolve)
- Policy enforcement
- SSO/audit logs (mentioned in pricing only)

---

## 14. Code-Quality Features

### Product surface (visual)

- Code quality page (`DataPage kind="quality"`)
- Code quality dashboard metric (87/100)
- Metrics: Quality score, Maintainability, Complexity, Duplication, Technical debt
- Findings table: Severity, Rule, File, Line, Category, Status
- Finding categories chart
- PR code quality tab (non-functional)
- Help guide card

### Mock findings

- `complexity-threshold`, `no-duplicate-branches`, `missing-error-context` rules

### Not implemented

- Linter integration
- Complexity analysis engine
- Technical debt calculation
- Quality gates on PRs
- Custom rule configuration

---

## 15. Dependency Features

### Product surface (visual)

- Dependencies page (`DataPage kind="dependencies"`)
- Metrics: Dependency health, Total packages, Outdated, Vulnerable, Abandoned
- Package table: Package, Current, Latest, Status, Vulnerability, License
- Package status chart
- Repo dependency health metric (derived in detail view)
- Attention signal: "7 dependencies need updates"
- Notification type: Dependency vulnerabilities

### Mock packages

- stripe, axios (vulnerable CVE-2026-1120), zod

### Not implemented

- Lockfile parsing
- License compliance reports
- Auto-PR for updates
- SBOM export
- Abandoned package detection logic

---

## 16. Analytics Features

### Product surface (visual)

- Analytics page (`DataPage kind="analytics"`)
- Metrics: PR throughput, Merge frequency, Review time, Average PR size, Average risk
- Defined metrics comparison table (current vs previous period)
- Delivery performance trend chart
- Team signals bar chart
- Export report button
- `Analytics` type with trend arrays in mock

### Mock analytics (`lib/mock/index.ts`)

```typescript
{
  range: '30d',
  prThroughput: 42,
  averageRisk: 32,
  averagePrSize: 14,
  timeToFirstReviewHours: 3.4,
  timeToMergeHours: 18.2,
  coverageTrend: [72, 74, 75, 77, 78, 79],
  qualityTrend: [78, 80, 81, 84, 85, 87],
  riskTrend: [44, 41, 39, 36, 34, 32]
}
```

### Not implemented

- Time-series storage
- Custom date ranges
- Team/repo breakdowns
- DORA metrics computation
- Report generation/export

---

## 17. Settings Features

### Two parallel implementations

1. **`/app/settings`** — `Settings` component with inline profile form + horizontal sub-nav (mostly non-navigating)
2. **`/app/settings/*`** — `SettingsSection` per route with dedicated content

### Sections

| Section | Fields / Content | Persistence |
|---------|------------------|-------------|
| Profile | Name, email, timezone | Local `saved` state |
| Team | 4 members with roles (Owner, Admin, Member, Viewer) | Static |
| Integrations | GitHub card — "Not connected · OAuth ready" + Connect | Static |
| Notifications | 5 toggle checkboxes | `defaultChecked` only |
| Security | 5 review links + delete account | Non-functional |

### Not implemented

- Team invitations
- Role management
- API keys
- Billing
- Workspace/org settings
- GitHub OAuth flow
- Webhook management
- Audit log viewer

---

## 18. Authentication Flows

### Demo flow (actual behavior)

```
Signup:
  AuthForm → validate → demoAuthAdapter.signup() → localStorage → /onboarding

Login:
  AuthForm → validate → demoAuthAdapter.login() → localStorage → /app/dashboard

Protected routes:
  ProtectedGate checks getSession() → redirect /login?next={pathname}

Logout:
  Not exposed in UI (adapter exists)

Forgot/Reset:
  Submit → success screen → "no real email" message → Continue
```

### Visual-only flows

- Continue with GitHub (login page)
- Real password reset email
- Session management in settings

### Auth adapter interface (`auth-adapter.ts`)

- `login`, `signup`, `logout`, `getSession`, `isAuthenticated`
- Designed for swap with real backend adapter

### Auth context (`auth-context.tsx`)

- `AuthProvider` + `useAuth` — **defined but not wired** into root layout

---

## 19. Onboarding Flow

**3 steps** (`Onboarding` component):

| Step | Title | Actions |
|------|-------|---------|
| 1 | Welcome to Verion | Skip setup → dashboard; Continue → step 2 |
| 2 | Connect GitHub | Back → step 1; Continue → step 3 |
| 3 | You're ready to ship safer | Back → step 2; Go to dashboard |

- No data collection
- No actual GitHub connection on step 2
- Skippable from step 1

---

## 20. Notification System

### UI presence

- Bell icon in topbar with red unread dot
- Mock `Notification[]` in `lib/mock/index.ts` (3 items)
- `notificationService.list` + `markRead` stubs
- Settings notification preferences (5 toggles)
- Attention-needed panel on dashboard (related but separate)

### Mock notifications

| Title | Severity | Read | Link |
|-------|----------|------|------|
| Critical vulnerability detected | critical | false | /app/security |
| PR #142 requires attention | high | false | /app/pull-requests/142 |
| Repository analysis completed | low | true | /app/repositories/commerce-api |

### Not implemented

- Notification dropdown/panel
- Mark as read UI
- Real-time push (WebSocket/SSE)
- Email delivery
- Notification routing rules

---

## 21. Command Palette

**Trigger:** ⌘K (desktop search bar), search icon (mobile)

**Contents:**
- Search input (placeholder: "Search repositories, pull requests, findings...")
- Navigate section: Dashboard, Repositories, Pull Requests, Code Quality, Security
- Footer tip: "use ⌘K anywhere to open search"

**Behavior:**
- Click outside closes
- Selecting item navigates and closes
- **No actual search/filter** across repos, PRs, or findings
- **No keyboard shortcut listener** registered globally (button-triggered only)

---

## 22. Responsive Behavior

| Breakpoint behavior | Implementation |
|---------------------|----------------|
| **Mobile (<md)** | Sidebar hidden off-screen; hamburger opens overlay; backdrop dismiss; table columns collapse to labeled stacks |
| **Tablet (md+)** | Sidebar fixed visible; search bar appears (sm:flex) |
| **Desktop (xl+)** | Dashboard 5-column metrics; 2-column layouts expand |
| **Landing** | lg:grid-cols-2 auth layout; md:flex marketing nav; responsive hero text (text-5xl → md:text-7xl) |
| **Auth** | Single column mobile; split panel on lg+ |
| **Tables** | `hidden md:grid` headers; mobile shows inline labels per cell |
| **PR tabs** | `overflow-x-auto` horizontal scroll |
| **Settings nav** | `overflow-auto` horizontal on mobile, vertical on lg |

Max content width: `max-w-[1500px]` in app main; `max-w-7xl` on marketing.

---

## 23. Dark / Light Theme

### Mechanism

- `Topbar` toggle: `document.documentElement.classList.toggle('dark', !dark)`
- Local React state `dark` — **not persisted**
- CSS variables in `globals.css` for `:root` and `.dark`
- `@media (prefers-color-scheme: dark)` auto-applies dark tokens when no `.light` class
- `color-scheme: light dark` on root
- `viewport.themeColor` adapts to system preference
- Icon swap: Sun (light) / Moon (dark) in topbar
- Tone colors have dark variants: `dark:text-emerald-400`, etc.

### Not implemented

- System preference sync on toggle
- localStorage persistence
- Theme in user settings

---

## 24. Accessibility Patterns

### Present

| Pattern | Where |
|---------|-------|
| `aria-label` on icon buttons | Menu, close, theme, notifications, search, metric help |
| `aria-label` on StatusDot | Tone label |
| `role="img"` + `aria-label` | SVG charts |
| `role="status"` | Loading states |
| `role="alert"` | Form errors |
| `aria-invalid` | Form fields with errors |
| `lang="en"` | Root HTML |
| Semantic `<nav aria-label="Main navigation">` | Sidebar |
| `aria-label="Repository sections"` | Repo detail tabs |
| Focus rings | `focus:ring-4 focus:ring-primary/10` on inputs |
| Button component | `focus-visible:ring-3` (unused component) |

### Gaps

- No skip-to-content link
- Command palette: no focus trap, no arrow-key navigation, no `role="dialog"`
- Tables lack `<th scope>` in DataPage
- Color-only status indicators (mitigated partially by text labels)
- No live regions for dynamic updates
- Mobile table labels rely on visual `<span className="md:hidden">` — acceptable
- Keyboard shortcut ⌘K not globally bound
- No reduced-motion preferences

---

## 25. Branding and Design Tokens

### Brand identity

| Element | Value |
|---------|-------|
| Product name | VERION (tracked caps, `tracking-[0.22em]`) |
| Logo mark | "V" in primary rounded square + cyan underline accent (`bg-cyan-300`) |
| Tagline | "Engineering intelligence for every code change." |
| Monospace | Used for scores, metrics, file paths, kbd |
| Icon library | Lucide React |

### Color system (CSS variables, OKLCH)

| Token | Light | Usage |
|-------|-------|-------|
| `--primary` | `oklch(0.49 0.22 275)` (indigo/violet) | CTAs, active nav, links |
| `--background` | `oklch(0.985 0.006 264)` | Page bg |
| `--foreground` | `oklch(0.19 0.025 264)` | Text |
| `--card` | white | Cards |
| `--muted` / `--muted-foreground` | gray tones | Secondary text, borders |
| `--destructive` | red-orange | Errors, danger |
| `--sidebar-*` | dedicated sidebar palette | Navigation |
| `--chart-1` through `--chart-5` | grayscale steps | Defined but unused in charts |
| Semantic tones | emerald (healthy), amber (warning), red (critical), cyan (accent) | Scores, badges, charts |

### Typography scale

- Page titles: `text-2xl md:text-3xl font-semibold`
- Section titles: `text-sm font-semibold`
- Eyebrows: `text-[11px] uppercase tracking-[0.16em] text-primary`
- Body: `text-sm`, meta: `text-xs` / `text-[11px]`
- Scores: `font-mono font-semibold`

### Spacing & shape

- `--radius: 0.625rem` (10px base)
- Derived: `--radius-sm` through `--radius-4xl`
- Cards: `rounded-xl border border-border/80 shadow-sm`
- Buttons/inputs: `rounded-lg`

### Component conventions

- shadcn/ui base-nova style (configured in `components.json`)
- Tailwind CSS v4 with `@theme inline`
- `cn()` utility for class merging
- Cards on muted background pattern
- Primary CTA: `bg-primary text-primary-foreground shadow-sm`

---

## Classification Matrix

### Purely visual (no business logic)

- All SVG/CSS charts and trend lines
- Marketing landing page content
- Pricing plans and feature bullets
- Hero dashboard preview on landing
- AI review credits sidebar widget
- PR activity bar chart and legend
- DataPage secondary bar charts
- Filter/sort dropdown buttons (repos, PRs, date ranges)
- Tab bars without content switching
- More options (⋯) buttons
- Notification bell dot (no panel)
- User/org dropdown chevrons
- Help guide cards (no content)
- Export report button
- MetricCard help (?) buttons
- Landing "Now analyzing 12,840 code changes" badge
- SOC 2-ready architecture claim

### Currently mocked (structured fake data)

| Data | Source |
|------|--------|
| Repositories (4) | `lib/mock/index.ts` + inline duplicates in `verion-app.tsx` |
| Pull requests (2 in mock, 4 inline) | `lib/mock/index.ts` + `verion-app.tsx` |
| Notifications (3) | `lib/mock/index.ts` |
| Analytics object | `lib/mock/index.ts` |
| Dashboard attention items | Hardcoded in `Dashboard` |
| DataPage table rows | Hardcoded per `kind` in `DataPage` |
| Settings team members | Hardcoded in `SettingsSection` |
| Repository analysis history | Hardcoded in `RepositoryDetail` |
| PR risk factors (rich detail) | Hardcoded in `PRDetail` |
| AI review findings | Hardcoded in `PRDetail` |

### Currently hardcoded (static strings/values)

- User: "Alex Morgan", "Engineering lead", initials "AM"
- Organization: "Acme Platform", "Engineering"
- Nav badge counts: PRs=12, Security=3
- Dashboard date: "Monday, August 12, 2026"
- All trend percentages in MetricCards
- PR activity counts: 48/36/7
- AI credits: 750/1000
- Repository security letter grades (A/B/C) — not in typed model
- Demo session user in `demo-auth-adapter.ts`
- Auth form default values (Alex Morgan, alex@acme.dev)
- CVE/CVE IDs in copy

### Reusable design patterns (worth preserving in production UI)

| Pattern | Description |
|---------|-------------|
| **App shell** | Fixed sidebar + sticky topbar + max-width content |
| **PageHeader** | Eyebrow + title + description + right-aligned actions |
| **MetricCard grid** | 5-up KPI row with sparkline and trend |
| **Tone system** | healthy / warning / critical / neutral with consistent colors |
| **Score + Badge** | Numeric scores with semantic coloring |
| **Attention feed** | Prioritized actionable signals with icons and deep links |
| **Data page template** | Metrics row + trend chart + breakdown + findings table |
| **List → detail navigation** | Table rows as clickable navigation targets |
| **Responsive data grid** | Desktop columns, mobile stacked labels |
| **Auth split layout** | Brand panel + form card |
| **Onboarding stepper** | Step N of 3 with skip |
| **Command palette** | Global search/navigation overlay |
| **Loading/Empty/Error states** | Consistent placeholder components |
| **Protected gate** | Redirect unauthenticated users with `next` param |
| **Service layer with mock fallback** | API abstraction pattern in `services.ts` |

### Actual business functionality (minimal, demo-only)

| Feature | Real behavior |
|---------|---------------|
| Client-side repo search | Filters by `name.includes(query)` |
| Demo auth login/signup | localStorage session after validation |
| Auth route protection | Redirect if no session |
| Theme toggle | Adds/removes `.dark` class |
| Onboarding step state | Increments/decrements step |
| Settings save feedback | Shows "saved" message locally |
| Browser back on detail pages | `history.back()` |
| Error boundary retry | Calls Next.js `reset()` |
| Password strength indicator | Client-side regex scoring |
| Form validation | Email, password length, confirm match, terms |

### Functionality that must eventually come from FastAPI

Mapped from `lib/api/services.ts` stubs and domain types:

| Domain | Endpoints (stubbed) | Backend responsibility |
|--------|---------------------|------------------------|
| **Auth** | `POST /auth/login`, `/auth/signup`, `/auth/logout` | Real credentials, JWT/session, password reset emails |
| **Repositories** | `GET /repositories`, `GET /repositories/:id` | GitHub sync, metadata, health scores |
| **Analysis** | `POST /repositories/:id/analyze` | Queue and run analysis jobs, progress |
| **Pull requests** | `GET /pull-requests`, `GET /pull-requests/:id` | Sync from GitHub, risk scoring, findings |
| **Security** | `GET /security/findings` | SAST, CVE correlation, secret scanning |
| **Code quality** | `GET /quality/findings` | Linting, complexity, debt metrics |
| **Dependencies** | `GET /dependencies` | Lockfile parsing, vulnerability DB |
| **Analytics** | `GET /analytics` | Aggregated metrics, time series |
| **Notifications** | `GET /notifications`, `PATCH /notifications/:id/read` | Event-driven alerts, read state |
| **Integrations** | `GET /integrations/github`, `POST /integrations/github/connect` | OAuth, webhooks, repo selection |
| **Team** | `GET /team/members` | RBAC, invitations, org management |

**Additional backend needs not stubbed in v0:**

- Risk score engine with explainable factors
- AI review generation with confidence scores
- Webhook event ingestion (push, PR, release)
- User profile and settings persistence
- Notification preference storage
- Audit logs
- Billing/subscription (pricing page implies tiers)
- Report export (PDF/CSV)
- Search index (command palette, global search)

---

## Technical Debt & Inconsistencies in Reference

1. **Dual PR detail implementations** — rich `PRDetail` in `verion-app.tsx` vs minimal `PullRequestDetail` used by routes
2. **Dual settings implementations** — `/app/settings` vs `/app/settings/*` sub-routes
3. **Duplicate mock data** — inline arrays in `verion-app.tsx` diverge from `lib/mock/index.ts`
4. **AuthProvider unused** — context defined but root layout doesn't wrap it
5. **Button component unused** — shadcn Button exists; all UI uses raw buttons
6. **VerionApp default export** — monolithic client router in `verion-app.tsx` partially superseded by App Router pages
7. **Public marketing routes** — `/features`, `/pricing`, etc. all render identical landing (no unique content)
8. **No tests, no CI config, no env example**

---

## File Map (Reference)

```
design-reference/verion/
├── app/                    # Next.js App Router pages
├── components/
│   ├── verion-app.tsx      # Main UI monolith (~90% of visuals)
│   ├── route-views.tsx     # Thin wrappers + ProtectedGate
│   ├── auth/auth-forms.tsx
│   ├── repositories/repository-detail.tsx
│   ├── pull-requests/pr-detail.tsx
│   ├── settings/settings-sections.tsx
│   ├── states.tsx
│   └── ui/button.tsx       # Unused primitive
├── lib/
│   ├── mock/index.ts       # Canonical mock data
│   ├── api/services.ts     # API stubs with mock fallback
│   ├── auth/               # Demo auth adapter
│   └── utils.ts
├── types/verion.ts         # Domain type definitions
└── app/globals.css         # Design tokens
```

---

## Recommendations for Production (Design-Only)

1. **Treat `verion-app.tsx` as a wireframe library** — extract visual patterns, not component structure
2. **Unify detail views** — use the rich PR detail design as the target UX
3. **Wire settings to sub-routes only** — eliminate duplicate Settings component
4. **Preserve the tone/color system** — production-ready semantic palette
5. **Implement command palette with real search** — backend search index required
6. **Replace decorative charts** with data-driven chart components fed by FastAPI time-series endpoints
