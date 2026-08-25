# Story 32 - Rebuild the Settings page to spec (shared settings_service + audit + all sections)

## Status
**In progress (local).** Second page in the blueprint pass
([`architecture/settings-page.md`](/home/pi/Desktop/architecture/settings-page.md) +
the master doc's "Settings Page Build Plan"). Owner: rebuild the full spec. Frontend is
server-rendered **Jinja** (not the spec's SPA) per the 2026-08-22 decision.

## Problem
Current Settings has real backends only for Health, Provider/Model (`config.yaml` write + runtime
restart), Session Health, Approvals, Timezone, File Locations. **Channels, Workspace Access, and
Admin Contact are UI-only shells** (look real, do nothing). Missing per spec: per-mutation **audit**,
**typed-confirm** on restart/destructive actions, a provider **credential store**, **identity-file
upload**, Workspace **OAuth/smoke**, **Tools summary** (MCP health), and the field-save lifecycle.

## Approach
Mirror the People pattern: a shared **`admin_api/settings_service.py`** owning config read/write
(structured YAML, preserve unrelated keys, atomic, **redacted** audit) used by both the Jinja
`/admin/settings` page and the JSON `/api/admin/settings/*` endpoints. Rebuild section by section per
the spec Build Order; **remove the fake UI-only shells** as each real one lands.

## Section plan (status / risk)
| Section | Plan | Guardrail |
|---|---|---|
| Health / status | keep; tidy to spec | safe |
| Session Health (caps) | keep; route through service + audit | safe |
| File Locations | keep; presence-only | safe |
| Runtime Controls | restart/reload + prompt-diagnostics toggle; **typed-confirm** | ⚠️ restart hits live agent — coordinate (rule 8); test config-write without restart |
| Provider & Model | route through service; `restart_required`; audit | ⚠️ `config.yaml` write |
| Provider **credentials store** | move keys out of `.env` into a governed store; presence-only | architecture — confirm store shape before building |
| Approvals (tool mode) | keep; audit | ⚠️ `config.yaml` write |
| Admin Contact | build real store + save/read-back | safe |
| Tools Summary | link + cached MCP health (read-only) | safe (read-only) |
| **Workspace Access** | UI + read-only status + service scaffold only | 🔴 **OAuth/MCP — needs Anthony (CLAUDE.md); do NOT authorize/wire** |
| Identity-file upload | super-admin only; validation; atomic write; restart notice | ⚠️ writes `souls/…`/`SOUL.md` |
| Channels | per-channel config schemas + `process_after` | architecture — confirm channel config ownership before building |

## Hard rules (from spec)
- Never print/return raw config, `.env`, OAuth tokens, API keys, channel secrets, expanded config.
- Blank secret fields = "keep existing"; secret status is presence-only.
- Writes go to **environment-owned** config (never the tracked template); structured parse, preserve
  unrelated keys, atomic, restrictive perms.
- Every mutation (accepted/rejected/failed/no-op) writes **redacted** audit.
- Typed confirmation for restart, disconnect, delete, provider switch, diagnostics save, identity upload.

## Acceptance
- Field-save lifecycle for every editable field; audit on every mutation; no secrets in any response.
- No fake UI-only sections remain. Workspace OAuth/MCP wiring explicitly deferred to Anthony.
- Gate deferred with commit/push per owner; browser-tested per section.

## Review
_(fill before commit/push: brooks-review + brooks-audit, then focused + full ruff/pytest.)_
