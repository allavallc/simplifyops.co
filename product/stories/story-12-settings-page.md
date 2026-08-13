# Story 12 - Settings Page

## Status
In progress — UI skeleton built, backend pending

## Source
`/home/pi/Desktop/architecture/settings-page.md` — consolidated final-state build story

## Goal
API-first operator control surface. `<CONTROL_API>` owns auth, validation, persistence, audit, runtime coordination, and JSON contracts. Admin client renders from typed JSON APIs. Must not require server-rendered HTML.

## Sections Required (per arch doc)

| Section | Contents |
| --- | --- |
| Health | Non-secret status for control API, agent runtime, memory service, database, internal health checks |
| Session Health | Channel message caps, retained tool-result guardrails, rough session-token guardrails |
| File Locations | Presence/status for runtime home, runtime config, tracked config template, SOUL_FILE — no raw config or secrets |
| Runtime Controls | Runtime restart/reload, prompt diagnostics toggle, restart-required notices, safe status feedback |
| Provider And Model | Provider connection state, active provider/model, context length, memory URL, API-key presence, connect/disconnect, switch |
| Channels | Per-channel enablement, public identifier, provider, processing mode, process-after, secret presence, session cap |
| Workspace Access | Shared OAuth state, connected-account mismatch warning, connect/disconnect, calendar test, smoke config/status, document-workspace |
| Admin Contact | Primary and optional secondary contact from active admin/super-admin people |
| Tools Summary | Link/status for Tools view, cached MCP health |

## API Contract (read endpoints first)
- `GET /api/admin/settings/overview`
- `GET /api/admin/settings/runtime`
- `GET /api/admin/settings/providers`
- `GET /api/admin/settings/channels`
- `GET /api/admin/settings/workspace`
- `GET /api/admin/settings/admin-contact`
- `GET /api/admin/tools/summary`

## Key Rules
- No `.env` variable per Settings field — config-file backed
- Tracked templates never overwrite live environment config
- Secrets show presence/status only — never raw values
- All mutations require non-secret audit
- Runtime restart/reload is explicit operator action
- Blank secret fields preserve existing values
- Do not expose raw Hermes compression internals

## Build Order (per arch doc)
1. Config ownership map + settings schemas + response redaction
2. Read endpoints
3. Shared service-layer writers with audit
4. Mutation endpoints one area at a time
5. Client sections over typed APIs
6. Field lifecycle tests per section
7. Browser verification
8. Local Docker verification before staging

## Current State
- Jinja template with 4 sections built (Runtime, Session Caps, Channels, Workspace)
- Needs to be expanded to all 9 sections
- Backend API routes not yet built
- Server-rendered Jinja is a temporary deviation — target is API-first SPA (Story 9)
