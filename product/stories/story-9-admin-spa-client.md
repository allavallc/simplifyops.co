# Story 9 - Admin SPA Client

## Status
In progress (2026-08-13) — **stack locked by Anthony: Vite + React + TypeScript**,
client-side SPA (NO server-rendered HTML). Built to static assets, served same-origin
by the FastAPI control plane, consuming `/api/admin/*` JSON. The current Jinja admin
is superseded surface-by-surface, starting with People (story-21).

### Decision (Anthony 2026-08-13)
- No server-rendered pages — emphatic. Framework choice left to me → Vite+React+TS.
- Served static by FastAPI, same-origin (no CORS).
- **The SPA IS the admin** (Anthony: "just replace the current page… don't care if
  old pages break"). Rebuild ALL admin pages in the SPA.

### Correction (2026-08-14) — visual style reverted to the original design
Anthony: the instruction was to port the pages to the API-first SPA pattern **and keep
the existing design**. My first SPA build wrongly introduced an invented dark theme and
dropped the icon sidebar / sticky headers / card styling. That was an unrequested design
change (violated "No Architecture Choices Without Asking" + "Explain Before Acting" +
"Minimal Code" — a stylesheet already existed).

Reverted: the SPA now **reuses the original design verbatim**:
- `admin-client/src/App.css` = a copy of `admin_api/static/styles.css` (light theme,
  `#f5f7fb` bg, blue `#275efe`, 18px radius cards, soft shadow).
- `admin-client/src/index.css` emptied (the Vite starter's dark `prefers-color-scheme`
  root + `#root{width:1126px;text-align:center}` were the source of the black look).
- `admin-client/src/Icon.tsx` = Heroicons ported verbatim from `templates/_icons.html`.
- `App.tsx` shell = original `.app-shell` / icon `.sidebar` / sticky `.topbar`.
- All pages switched to the original class names (`.page-intro`, `.card`, `.table-card`,
  `.button`, `.status-pill`, `.detail-grid`, `.detail-card`, `.form-grid`, `.filter-btn`);
  each page's data-fetching is unchanged. A tiny `utils.css` adds only non-visual helpers
  (`.muted`/`.center`/`.nowrap`/`.row-inactive`).
Builds clean; `/app/` serves the light bundle (`index-Pg1EmAav.css`).

### Progress (2026-08-14)
- **Consolidation done:** login + `/admin` + `/admin/people` now 307 → `/app/`.
  The SPA is the admin entry point; old Jinja routes are superseded (some still
  resolve by direct URL until removed).
- **Full nav shell** in the SPA: People, Companies, Inbox, Activity, Knowledge,
  Memories, Tools, Automations, Job Credentials, Settings.
- **People** — fully rebuilt (story-21): index/detail/create/edit/deactivate.
- **Settings** — rebuilt over the working backends via `GET /api/admin/settings/state`
  + existing PATCH endpoints: Overall status (health), Provider+Model, Tool approvals
  (+manual warning), Session cap, Org timezone. File Locations / Channels / Workspace /
  Admin Contact shown as "not yet migrated" (honest; those backends are UI-only today).
- **All pages rebuilt in the SPA (2026-08-14):**
  - **Inbox** — real: list + status filter, approve/ignore/reject via `/api/inbox`.
  - **Activity** — real: list + status filter (`/api/activity`) + detail view
    (`/api/activity/{id}`, message/reply/error).
  - **Tools** — real: `GET /api/admin/tools` reads MCP servers from config.yaml
    (name/service/command/enabled, non-secret).
  - **Memories** — real: `GET /api/admin/memories/banks` proxies Hindsight
    (`/v1/default/banks`): bank, fact_count, last-document, updated.
  - **Companies, Knowledge, Automations, Job Credentials** — honest structured
    stubs (`StubTable`): intended columns + empty state, no fabricated rows. These
    four genuinely need NEW DB tables (a schema/backend build per their specs), not
    just a UI — flagged for their own stories.
- **AGENTS.md rule 2a added:** DO NOT BUILD SERVER-SIDE HTML — admin is API-first
  SPA only.
- Everything builds + serves; Inbox/Activity APIs verified 401-gated.

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
