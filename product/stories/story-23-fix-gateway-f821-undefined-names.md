# Story 23 - Fix 3 F821 undefined-name bugs in gateway.py (dead people-whitelist webhook refs)

## Owner
**C1** — `gateway.py` is C1's file (stories 15/17/19), and these are leftovers from the
people-whitelist removal C1 performed. The fix needs intent only C1 has (see below).

## Status
**Proposed — awaiting C1.** Found by ruff (`F821`) when the tooling was set up (story-24 groundwork).

## Problem
`ruff check . --select F821` reports **3 undefined-name errors, all in
`gateway/gateway.py` → `enrich_identity()` (lines 526–533):**
- `WHITELIST_WEBHOOK_SECRET` (used at 528 and 529)
- `WHITELIST_WEBHOOK_URL` (used at 531, `requests.post(WHITELIST_WEBHOOK_URL, ...)`)

These names are **never defined** — they're dead references to the old people-whitelist
webhook, which was removed when `people-whitelist.service` was deleted. At runtime, if
`enrich_identity()` is ever called, it raises `NameError`. This is a **real latent bug**, not
a style nit, and ruff can't auto-fix it.

## Decision required (C1)
Determine what `enrich_identity()` should do now that the whitelist webhook is gone:
1. **Remove** — if identity enrichment via the whitelist webhook is obsolete, delete the dead
   branch / function and any now-unused callers.
2. **Repoint** — if enrichment is still wanted, wire it to whatever replaced the whitelist app
   (define the URL/secret from config/env), and add a test.

## Acceptance
- `./.venv/bin/ruff check . --select F821` reports **0 errors**.
- No `NameError` path remains in `enrich_identity()`; behavior (removed or repointed) is
  intentional and covered by a test if the function is kept.
- Gate: `brooks-review` + `brooks-audit` clean, then focused + full `ruff`/`pytest` green
  (per AGENTS.md rules 2/9). Coordinate with C2 on `gateway.py` timing (overlaps story-24).

## Review
_(fill before commit/push per AGENTS.md: brooks-review + brooks-audit scores/Criticals, then
focused + full ruff/pytest green.)_

## Notes
Sibling: [[story-24]] handles the mechanical ruff fixes (imports/unused) across the repo,
including `gateway.py` — sequence so the two don't clobber each other in that file.
