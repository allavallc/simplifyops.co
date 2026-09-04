# Story 59 - Google OAuth Connection Management

## Status
**Increment 1 done (branch `story-59-google-oauth-management`)** — governed connect/callback/status/
disconnect + Settings Workspace wiring. **Deferred to a later increment** (no consumer yet): automatic
token refresh + `get_fresh_google_token()` (the current third-party Google MCP self-manages its own
OAuth; these tokens are consumed once repo-owned connectors land — [[story-55]]) and the calendar
smoke test.

## Operational setup (owner — required before Connect works)
- In the **Google Cloud Console** OAuth client, add the workspace callback as an authorized redirect
  URI: `<base>/integrations/google/callback` (distinct from the login `/auth/callback`). Optionally set
  `GOOGLE_WORKSPACE_REDIRECT_URI` in `relay.env` to pin it; otherwise it's derived from
  `GOOGLE_REDIRECT_URI`.
- The consent grant is broad (Calendar/Gmail/Drive/Sheets) — connecting is a deliberate owner action.

## Implemented
- `admin_api/google_workspace.py` — `build_auth_url` (pure; offline+consent → refresh_token),
  `exchange_code`, `store_tokens` (upsert `google_tokens`, keeps existing refresh_token if Google omits
  one), `get_status` (scopes+expiry+expired, **never tokens**), `revoke_and_disconnect` (best-effort
  revoke → delete).
- `admin_api/routes/integrations.py` — `/integrations/google/{connect,callback,status,disconnect}`,
  admin-gated, `state` CSRF check, audited (`google_workspace_connect`/`disconnect`).
- Settings → Workspace: real Disconnect (confirm → POST → reload); smoke test disabled with an honest
  "with connectors (story 55)" note.
- `tests/test_google_workspace.py` — `build_auth_url` (offline/consent/scopes/state/redirect) + the
  workspace redirect URI is separate from login.

## Review
Raw access/refresh tokens are never logged or returned (status exposes scopes + expiry only); separate
redirect URI + `state` CSRF; disconnect revokes best-effort then deletes. Refresh/`get_fresh_google_token`
**deliberately not built** (no consumer — avoids scaffolding, CLAUDE.md). brooks-review/audit: clean
service seam (lazy db/authlib/httpx imports for CI-testable pure `build_auth_url`), no cycles/dup. 🟡
the OAuth exchange/store/disconnect need live Google + DB so aren't unit-tested (only `build_auth_url`
is) — verified via app import; full flow is a manual owner test after the GCP redirect URI is
registered. No 🔴. **Gate:** rebased on `origin/main`; full ruff clean; pytest 31 green (2 new); app
imports (81 routes).

## Problem
MCP tools for Google Workspace (Calendar, Gmail, Drive, Sheets) need OAuth tokens to call provider APIs on behalf of the operator. There is no governed OAuth connection flow, no token storage, and no refresh mechanism. Without this, MCP tools cannot authenticate.

## Goal
Admin-managed Google OAuth connections. Anthony connects his Google account through the admin UI, tokens are stored in the DB, and MCP tools retrieve fresh tokens via a governed service call. Token refresh happens automatically before expiry.

## What Already Exists
- `google_tokens` table — `person_email`, `access_token`, `refresh_token`, `token_expiry`, `scopes`
- Google OAuth client credentials already in `relay.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
- Admin login already uses Google OAuth — this story extends it with additional scopes

## Required Scopes
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/drive`
- `https://www.googleapis.com/auth/spreadsheets`

## What To Build

### Admin API
- `GET /api/integrations/google/status` — is a token stored, what scopes, is it expired
- `GET /api/integrations/google/connect` — initiates OAuth flow with workspace scopes
- `GET /api/integrations/google/callback` — receives code, exchanges for tokens, stores in `google_tokens`
- `POST /api/integrations/google/disconnect` — revokes and deletes token
- Internal: `get_fresh_google_token(person_email)` — returns access token, refreshes if within 5 min of expiry

### Admin UI
- Integrations page: show Google connection status (connected/disconnected, scopes, expiry)
- Connect / Disconnect button
- No raw tokens displayed anywhere

### Token Refresh
- Before returning a token, check `token_expiry`
- If within 5 minutes of expiry or already expired, use `refresh_token` to get a new `access_token`
- Update `google_tokens` row with new access_token and expiry
- If refresh fails (revoked), mark as disconnected and notify operator

### Audit
- Log connect, disconnect, and refresh-failure events (no token values in logs)

## Key Constraints
- Never log, display, or return raw access_token or refresh_token
- OAuth callback must use the same redirect URI registered in Google Cloud Console
- Separate OAuth redirect URI from the admin login one (different callback path)
- Token refresh must be atomic — concurrent requests should not double-refresh
- MCP tools access tokens only through `get_fresh_google_token()`, never directly from DB

## Next Story
Story 9 (MCP Connector Framework) uses `get_fresh_google_token()` to authenticate provider API calls.
