# Story 5 - FastAPI Control Plane

## Status
Completed 2026-08-09 (Phase 1-3), Phase 4 (admin client SPA) pending

## Problem
The Node.js people-whitelist app was a co-owner of governance data alongside the gateway. There was no canonical `POST /messages` intake boundary. The admin UI was a static SPA calling the Node.js API. Two services writing to the same tables was a split-brain risk.

## Goal
Replace Node.js with a FastAPI control plane that owns `POST /messages`, governance, audit, and admin UI. Atomic cutover — no long-lived parallel write authorities.

## What Was Built
- `admin_api/` — FastAPI app on port 3000
- `POST /messages` — canonical governed intake: person_identities lookup → governance → work_items enqueue
- `/api/people` — CRUD with person_identities sync and audit logging
- `/api/inbox` — unknown sender queue with approve/reject/ignore
- `/api/activity` — work item log with detail view
- `/auth/login|callback|logout` — Google OAuth
- Jinja2 server-rendered admin pages (note: arch doc says API-first SPA is the target — see Story 6)
- `person_identities` table seeded from existing `telegram_id` values
- `admin_settings` table for global config
- `audit_log` entries at all key governance gates
- Node.js `people-whitelist.service` disabled
- Telegram adapter now calls `POST /messages` instead of `enqueue_message()` directly

## Pending
- Story 6: migrate Jinja templates to API-first SPA (arch doc requirement)
- Google OAuth redirect URI needs to be added to Google Cloud Console

## Key Files
- `admin_api/main.py`, `admin_api/routes/`
- `admin_api/schema.sql`
- `/etc/systemd/system/simplifyops-admin.service`
