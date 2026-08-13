# Story 9 - Admin SPA Client

## Status
Not started — current Jinja templates are a temporary deviation from arch doc

## Problem
The arch doc (brain-whitelabel-arch-build-doc.md) requires an API-first admin client — a separate browser client consuming JSON APIs, not server-rendered HTML. The current Jinja templates require server-side rendering and cannot be deployed separately.

## Goal
Replace Jinja templates with a static SPA (React or Vite) served by the FastAPI control plane as static build output, consuming the existing `/api/*` JSON routes.

## Views Required (per arch doc)
- Login / public home
- Status — runtime health, session health, channel status
- Settings — provider/model, channel setup, session caps
- Tools — MCP tool toggles, MCP health checks
- People — records, authority, identities, access flags
- Companies — hierarchy, archived state
- Inbox — unknown senders, approve/reject/ignore
- Activity Logs — request trace by request_id
- Activity Detail — one request end-to-end
- Knowledge — curated protocol docs
- Memories — Hindsight inspection
- Automations — scheduled/run-once work, status, notifications
- Job Credentials

## Notes
- All mutation must go through documented API contracts
- Never render raw tokens, OAuth material, or expanded config
- Existing `/api/*` routes are already built — this is a frontend-only story
- CORS must be defined if client is on a different origin
