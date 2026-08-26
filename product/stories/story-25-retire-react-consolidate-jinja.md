# Story 25 - Retire the React SPA; consolidate the admin UI on server-rendered Jinja

## Status
**Core done (local, uncommitted).** Reverses [[story-9-admin-spa-client]] and AGENTS.md rule 2a.
Decision: owner, 2026-08-22 — **no React, no SPA, no build step; admin UI is server-rendered Jinja.**
C1 (who built the SPA) is shut down; owner directed taking over C1's work and converting it to the
agreed direction (2026-08-23).

## Problem
The admin surface existed **twice**: a React SPA (`admin-client/`, served at `/app`) and the
server-rendered Jinja pages (`admin_api/templates/`, served at `/admin`). C1 built Jinja first, then
layered React on top and redirected `/admin` → `/app/`. The owner chose Jinja as the single,
low-maintenance direction (no framework, no build step).

## Key finding
The full Jinja admin **already exists** — 17 templates (incl. `people/{index,form,view}`,
`memories`, `tools`, `activity`, `activity_detail`, `inbox`, `settings`) and complete server-rendered
page routes in `main.py`. There was **no parity gap to build**. "Convert to Jinja" = peel the React
layer back off and keep C1's backend.

## What was done (take-over)
**Kept (C1's backend — API-first, aligns with arch rule 1):**
- `admin_api/routes/admin_people.py` / `admin_tools.py` / `admin_memories.py` (JSON `/api/admin/*`)
- `admin_api/routes/settings.py` `get_state` + default-timezone endpoints
- `admin_api/schema.sql` `first_name`/`last_name` split (story-21)
- Re-wired the three backend routers into `main.py` (imports + `include_router`).

**Removed (React):**
- Deleted `admin-client/` (backed up: `/home/pi/c1-backup-20260823-151024/admin-client.tgz`).
- Reverted `main.py` to the pure-Jinja entry (`/` → `/admin`, `/admin` renders `admin/index.html`,
  `/admin/people` uses the real handler); dropped the `/app` SPA mount. (C1's React main.py diff
  saved at `.../main.py-c1-react.patch`.)
- Reverted `auth.py` login redirect `/app/` → `/admin`.
- Dropped the stale `admin-client` entry from `pyproject.toml` ruff `extend-exclude`.

**Verified:** all `admin_api` compiles; no `/app`/`admin-client` refs remain in code or templates;
take-over added **zero** new ruff violations (`main.py` 16 == HEAD 16).

## Follow-ups (not blocking this story's core)
1. **Dead/duplicated JSON API.** With React gone, `/api/admin/people|tools|memories` have **no live
   consumer**, and `admin_people.py` duplicates the Jinja `/admin/people` pages (arch rule 1 / R3).
   Decision needed: keep them as a public/tool-facing API, or remove as dead code. (Kept for now per
   "take over the backend.")
2. **Ruff baseline** (unused `Jinja2Templates` in `main.py`, unused `token` in `auth.py`, etc.) —
   pre-existing story-24 territory, now includes C1's files.

## Acceptance
- [x] `/admin` is the sole admin UI (Jinja); `/app` gone; `admin-client/` removed.
- [x] No npm/Vite/React build step; backend JSON API preserved.
- [ ] Gate: `brooks-review` + `brooks-audit` clean, then focused + full `ruff`/`pytest`
  (deferred with commit/push per owner) — resolve follow-up #2 here.

## Review
_(fill before commit/push: brooks-review + brooks-audit scores/Criticals, then focused + full
ruff/pytest green.)_

## Notes
Supersedes [[story-9-admin-spa-client]]. AGENTS.md rule 2a + `product/product-decisions/current-architecture.md` arch
rules already updated to the Jinja direction.
