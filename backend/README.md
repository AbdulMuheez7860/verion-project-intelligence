# Verion Backend

FastAPI + MongoDB API for the Verion engineering intelligence platform.

## Milestone 2: GitHub Integration

```
Connect GitHub → OAuth → Select repository → Webhook → Celery → Analysis job
```

Stack: **FastAPI · MongoDB · Redis · Celery**

### GitHub OAuth setup

1. Create a [GitHub OAuth App](https://github.com/settings/developers)
2. Set callback URL: `http://localhost:8000/api/v1/integrations/github/callback`
3. Copy credentials to `.env`:

```env
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_WEBHOOK_SECRET=change-me-webhook-secret
```

### Integration endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/integrations/github` | Connection status |
| POST | `/api/v1/integrations/github/connect` | Start OAuth (returns `authorizeUrl`) |
| DELETE | `/api/v1/integrations/github` | Disconnect GitHub |
| GET | `/api/v1/integrations/github/repositories` | List repos available to connect |
| POST | `/api/v1/repositories` | Connect a repository (`{ githubId }`) |
| DELETE | `/api/v1/repositories/{id}` | Disconnect repository |
| POST | `/api/v1/webhooks/github` | GitHub webhook receiver (signature verified) |

### Analysis pipeline

1. Repository connect or webhook (`push`, `pull_request`) enqueues a Celery job
2. Worker syncs real metadata from GitHub (language, open PRs)
3. Status transitions: `queued → running → complete | failed`
4. **No fabricated scores** — health/security scores remain null until scanner tools run

### Docker services

```bash
docker compose up --build   # mongodb, redis, backend, worker
```

## Structure

```
app/
  main.py
  core/          config, security, database
  api/           route handlers
  schemas/       Pydantic models (camelCase JSON)
  repositories/  MongoDB data access
  services/      business logic
  utils/
tests/
```

## Local development

### With Docker Compose (recommended)

From the repository root:

```bash
docker compose up --build
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### Manual

1. Start MongoDB on `localhost:27017`
2. Copy `.env.example` to `.env`
3. Install and run:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend integration

The Vite dev server proxies `/api` to `http://localhost:8000`. Start both:

```bash
# terminal 1
docker compose up

# terminal 2
cd frontend && npm run dev
```

Auth uses HTTP-only session cookies — never localStorage:

| Cookie | Purpose | Lifetime |
|--------|---------|----------|
| `verion_session` | Short-lived access JWT | 15 minutes |
| `verion_refresh` | Refresh JWT | 7 days |

### Auth endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/signup` | Create user, organization, owner membership |
| POST | `/api/v1/auth/login` | Authenticate and set cookies |
| POST | `/api/v1/auth/logout` | Clear session cookies |
| POST | `/api/v1/auth/refresh` | Rotate cookies using refresh token |
| GET | `/api/v1/auth/me` | Current session (user + organization + membership) |

Signup/login/me responses return a `SessionResponse`:

```json
{
  "user": { "id": "...", "name": "...", "email": "..." },
  "organization": { "id": "...", "name": "...", "slug": "..." },
  "membership": { "id": "...", "organizationId": "...", "role": "owner" }
}
```

## Tests

Requires MongoDB on `localhost:27017`:

```bash
cd backend
pip install -r requirements.txt
pytest
```
