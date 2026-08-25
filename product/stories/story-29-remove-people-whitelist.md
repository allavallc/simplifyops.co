# Story 29 - Remove the disabled legacy `people-whitelist/` Node app

## Status
**Done (local, uncommitted).** Addresses the R4 dead-module 🟡 finding from the 2026-08-22
architecture audit. `people-whitelist/` removed (tracked via `git rm` + untracked leftovers
`rm -rf`'d — `certs/`/`uploads/` were empty, `.env` was a symlink, real repo `.env` intact).
No code references remained; systemd unit already gone (C1). Docs updated: CLAUDE.md,
`ops/current-architecture.md`, AGENTS.md. The build blueprint's "Old Mistakes" backs this
(no parallel governance writer). Stale planning mentions in `todo.md`/`plan-architecture/backlog.md`
left as historical notes.

## Problem
`people-whitelist/` is a Node/Express admin app (its own `server.js`, `src/`, SQL schema, and a
`people-whitelist.service` unit) that is documented as **DISABLED and replaced by `admin_api/`**
(CLAUDE.md; `ops/current-architecture.md`). It remains in the tree with a second, stale "people"
data model and its own `/internal/reply` contract — dead code that invites accidental edits,
confuses the dependency picture, and inflates onboarding load.

## Proposed approach
1. **Confirm nothing live references it** — grep the repo and the gateway for
   `people-whitelist`, port `3000` (Node), and the `/internal/reply` callback path; verify the
   FastAPI `admin_api` fully owns the inbox/approval flow (it does, per governance section of
   `ops/current-architecture.md`).
2. **Confirm the service is truly disabled** — `systemctl is-enabled people-whitelist.service`
   (expected: disabled/masked). Do **not** touch the unit file (NEVER delete/mask service files
   per CLAUDE.md) — this story only removes the repo directory.
3. **Delete `people-whitelist/`** from the repo (recoverable from git history).
4. Update CLAUDE.md and `ops/current-architecture.md` to drop the "replaced by admin_api" line's
   in-tree reference (keep the historical note that it *was* replaced).

## Acceptance
- `people-whitelist/` no longer in the repo; no repo code references it.
- The disabled `people-whitelist.service` unit is left untouched on the host.
- Gate: `brooks-review` + `brooks-audit` clean, then focused + full `ruff`/`pytest`, on a
  `story-29-…` work branch (rule 10).

## Review
_(fill before commit/push: brooks-review + brooks-audit scores/Criticals, then focused + full
ruff/pytest green.)_

## Notes
Coordinate on shared infra (services) per rule 8 before starting.
