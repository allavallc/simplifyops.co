# Backlog

## On Hold

- **Cost tracking via Anthropic Admin API** (started 2026-04-05)
  - Files created: `server/src/services/anthropic-cost-tracker.ts`, heartbeat.ts patch applied
  - Blocked: API key org mismatch — Hermes uses a different org than the admin key
  - Admin key stored in: `/workspace/simplifyops/.env` (ANTHROPIC_ADMIN_API_KEY)
  - Resume: Sort out API key/org, rebuild server, test cost tracking

## Pending

- **Inbox status filter** (2026-04-06)
  - Code complete in `ui/src/pages/Inbox.tsx`
  - Waiting: Docker rebuild (crashed with bus error)
  - Resume: Restart Docker, run `docker compose up -d server --build`
