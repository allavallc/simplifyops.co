# Story 35 - Slim admin_api/main.py to a composition root (extract Jinja page routes)

## Status
**Done (local, verified live — 2026-08-25).** Resolves the 🟡 `main.py` finding from the
architecture audit (R1 Cognitive Overload — composition root mixed with all page routes).

## Problem
`admin_api/main.py` (540 lines) was the app factory + lifespan + middleware + router wiring **and**
held every server-rendered Jinja page route (login, `/admin`, people, inbox, activity, settings,
knowledge, memories, companies, tools, automations, job-credentials) plus the `render`/`_guard`/
`_user`/`_actor` helpers and the Jinja templates env. Composition root and UI concerns intertwined.

## What was done
- New **`admin_api/routes/pages.py`** — one `APIRouter` holding the templates env, the
  render/guard/user/actor helpers, and all 25 server-rendered page routes (verbatim behavior;
  `@app.*` → `@router.*`).
- `main.py` → **58 lines**: imports, `SessionMiddleware`, router includes (now incl. `pages_router`),
  `/static` mount, lifespan. No page routes, no templates env.
- Verified: route count unchanged (69), full **ruff clean**, **pytest green**, admin restarted
  clean, every `/admin/*` page returns 307 (auth redirect) not 500.

## Acceptance
- [x] `main.py` is wiring-only; page routes live in `routes/pages.py`.
- [x] No behavior change (same routes, same renders); ruff + pytest green.
- [x] Gate: focused + full ruff/pytest green; brooks findings for `main.py` resolved.

## Review
Static review: pure move + `@app`→`@router` rename; behavior preserved; route count identical (69);
templates env relocated (BASE_DIR = admin_api/). ruff clean, pytest 6/6, live smoke (health 200,
pages 307). No 🔴.
