# Verion Frontend

Phase 1 React application for the Verion engineering intelligence platform.

## Structure

```
src/
  app/              App.tsx, router, providers
  api/              HTTP client and domain API modules
  components/
    ui/             shadcn-style primitives
    layout/         shell, page header, auth layout
    navigation/     sidebar, topbar, logo, nav config
    charts/         metric cards (data-bound, no fake charts)
    tables/         findings and package tables
    forms/          shared form components
    states/         loading, empty, error
  features/         domain pages (auth, dashboard, repos, etc.)
  hooks/
  types/
  lib/              utilities
  styles/           global CSS and design tokens
  main.tsx
```

## Principles

- **No fake metrics** — all scores come from the FastAPI backend or show **Unavailable**
- **No monolithic files** — no `verion-app.tsx`; features are split by domain
- Business logic lives in `api/`, not React components

## Development

```bash
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000`.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Typecheck + production build |
| `npm run lint` | Run oxlint |
