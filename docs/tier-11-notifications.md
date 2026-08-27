# Tier 11 — Notifications, Alerts & Event Intelligence

## Overview

Tier 11 connects real engineering events to a persisted in-app notification system with user preferences, unread state, and deep links.

## API

- `GET /api/v1/notifications` — paginated list (user-scoped)
- `GET /api/v1/notifications/unread-count`
- `PATCH /api/v1/notifications/{id}/read`
- `POST /api/v1/notifications/mark-all-read`
- `GET /api/v1/notification-preferences`
- `PUT /api/v1/notification-preferences`

## Event types

| Type | Severity | Trigger |
|------|----------|---------|
| `security.critical_finding` | critical | Analysis finds critical security findings |
| `dependency.critical_vulnerability` | critical | Critical dependency issues |
| `pr.high_risk` | high/critical | Open PR risk score ≥ 50 |
| `quality.regression` | warning | Material quality score decline |
| `health.regression` | warning | Material health score decline |
| `analysis.completed` | info | Analysis run completes |
| `analysis.failed` | critical | Analysis run fails |
| `analysis.stale` | warning | No completed analysis in 7+ days |
| `workspace.*` | info | Member/invitation events (admins) |
| `integration.*` | info | GitHub connect/disconnect (admins) |

## Architecture

- `notifications` collection — per-user copies with idempotency keys
- `notification_preferences` — per-user in-app channel toggles
- `NotificationEventService` — fan-out with preference filtering and deduplication

## Limitations

- In-app only — no email, SMS, Slack, or push
- Workspace alerts delivered to admins/owners only
- No real-time WebSocket (30s polling for unread count)
