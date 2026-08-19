# Story 23 - Fix 3 F821 undefined-name bugs in gateway.py (dead people-whitelist webhook refs)

## Owner
**C1** — `gateway.py` is C1's file (stories 15/17/19), and these are leftovers from the
people-whitelist removal C1 performed. The fix needs intent only C1 has (see below).

## Status
**Code complete (2026-08-19)** on branch `chore/brooks-lint-review-gate` (the tooling
branch — where ruff/brooks/pytest live; Anthony-approved location since the gate isn't on
`main` yet). Decision: **remove** (Anthony-approved). Not yet pushed/merged/archived — that
rides with the tooling branch's own merge, a bundle-level call above this story.
Found by ruff (`F821`) when the tooling was set up (story-24 groundwork).

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
**Decision (Anthony, 2026-08-19): Remove.** `enrich_identity()` had **zero callers**
(`grep -rn enrich_identity` = definition only) and `WHITELIST_WEBHOOK_URL` /
`WHITELIST_WEBHOOK_SECRET` were referenced *only* inside it — dead leftovers of the
people-whitelist webhook removed 2026-08-14. "Repoint" had no target (the whitelist app is
superseded by the SPA + `/api/inbox` → `queue_contact_request()`, which is separately wired
and untouched). Fix = delete the function + its section header (−16 lines, 0 added).

- **brooks-review (PR Review):** Health Score **100/100**, **0 findings** (0 Critical).
  Pure deletion of dead code; scanned R1–R6, nothing added. Quick Test Check skipped
  (deleted fn had 0 callers / 0 tests).
- **brooks-audit (Architecture Audit):** Health Score **100/100**, **0 findings**
  (0 Critical). Removed node had no inbound edges; layering/seams unchanged, structural
  honesty improved.
- **ruff `--select F821` (acceptance):** focused (gateway.py) **and** full-repo → **0 errors**.
- **pytest:** full suite **green** (`test_transcription.py`, all pass). No gateway test added —
  the function was removed, not kept, so there is nothing to cover (matches Acceptance).
- **Residual full-ruff findings NOT owned here:** full `ruff check .` still reports 31
  mechanical `I001`/`F401` errors (incl. gateway.py's pre-existing import-sort + unused `re`).
  **Verified pre-existing** (present on committed gateway.py before this change via
  `git stash` A/B) and assigned to **[[story-24]]** (C2's mechanical `--fix` pass). Left
  untouched to honor the story-23→story-24 sequencing agreed in `agent-coordination.md`
  (fixing them here would clobber C2's diff). This story's own change adds **no** new lint.

## Notes
Sibling: [[story-24]] handles the mechanical ruff fixes (imports/unused) across the repo,
including `gateway.py` — sequence so the two don't clobber each other in that file.
