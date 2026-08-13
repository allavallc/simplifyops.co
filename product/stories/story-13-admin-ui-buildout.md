# Story 13 - Admin UI Build-Out (left icon sidebar + missing pages)

## Status
In progress — UI only, no backend code

## Goal
Build all missing admin pages as UI shells, convert the top nav to a left-side
icon-driven sidebar using Heroicons (inline SVG via a Jinja macro), and track
per-page approval so we can review one by one later.

## Design Conventions (documented here for the whole site)
- **Icons: Heroicons**, delivered as **inline SVG** through a Jinja macro
  (`templates/_icons.html`, used as `{{ icon("name") }}`). No CDN, no npm, no
  build step — self-contained, works offline.
- **Navigation: left-side icon rail.** Icon + label, active state highlighted.
  Collapses to a top bar or hamburger on mobile (desktop + mobile both required
  per arch doc).
- Existing card / table / status-pill styles reused across all pages.
- **Sticky headers, site-wide:** the topbar, each page's `<h1>` header block, and
  every `<table class="data-table">` column header (`thead th`) stay pinned on
  scroll (`position: sticky` in `static/styles.css`).
- UI-only pages use disabled controls labelled "backend not yet implemented"
  and empty states — never fake data.

## Approval Tracking

| Page | Route | Built | Approved | Notes |
|---|---|---|---|---|
| Login | `/` | ✅ | ⬜ | Google OAuth working |
| Dashboard | `/admin` | ✅ | ⬜ | pending inbox count |
| People (index/view/form) | `/admin/people` | ✅ | ⬜ | full CRUD backend |
| Inbox | `/admin/inbox` | ✅ | ⬜ | approve/reject/ignore backend |
| Activity + Detail | `/admin/activity` | ✅ | ⬜ | work item trace backend |
| Settings · Health | `/admin/settings` | ✅ | ✅ | approved |
| Settings · Provider+Model | `/admin/settings` | ✅ | ✅ | approved |
| Settings · Session Health | `/admin/settings` | ✅ | ⬜ | cap save backend |
| Settings · Runtime Controls | `/admin/settings` | ✅ | ⬜ | UI only |
| Settings · File Locations | `/admin/settings` | ✅ | ⬜ | UI only |
| Settings · Channels | `/admin/settings` | ✅ | ⬜ | UI only |
| Settings · Workspace | `/admin/settings` | ✅ | ⬜ | UI only — MCP paused |
| Settings · Admin Contact | `/admin/settings` | ✅ | ⬜ | UI only |
| Settings · Tools Summary | `/admin/settings` | ✅ | ⬜ | UI only |
| Left icon sidebar | (global) | ✅ | ⬜ | Heroicons inline SVG macro; sticky topbar |
| ~~Status~~ (removed) | — | — | — | Folded into Settings as "Overall status" (Health) section per Anthony — no standalone page |
| Knowledge | `/admin/knowledge` | ✅ | ⬜ | UI only; sticky headers |
| Memories | `/admin/memories` | ✅ | ⬜ | UI only; sticky headers |
| Companies | `/admin/companies` | ✅ | ⬜ | UI only; sticky headers |
| Tools | `/admin/tools` | ✅ | ⬜ | UI only; sticky headers |
| Automations | `/admin/automations` | ✅ | ⬜ | UI only; sticky headers |
| Job Credentials | `/admin/job-credentials` | ✅ | ⬜ | UI only; sticky headers |

Legend: ✅ done · ⬜ not yet · approval set only when Anthony says "approved".

## Out of Scope
- All backend logic for the new pages
- MCP/Workspace OAuth (paused pending other-LLM guidance)
