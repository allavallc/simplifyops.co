# Story 24 - Ruff baseline cleanup (mechanical: imports + unused) so `ruff check .` is green

## Owner
**C2** — mechanical/auto-fixable changes. Coordinated with C1 (touches C1's files).

## Status
**Proposed.** Blocked on coordination (see Dependencies).

## Problem
Setting up ruff (story: ruff/pytest tooling) surfaced **34** violations repo-wide; the
pipeline's "full `ruff`" gate can't pass until the baseline is clean. This story clears the
**31 mechanical, auto-fixable** ones (the 3 real `F821` bugs are **out of scope** → [[story-23]]):

| Rule | Count | Fix |
|---|---|---|
| `I001` unsorted-imports | 21 | `ruff check --fix` (safe reorder) |
| `F401` unused-import | 9 | `ruff check --fix` (review each — imports can have side effects) |
| `F841` unused-variable | 1 | manual (assign-and-drop) |

Affected files: `admin_api/routes/messages.py`, `admin_api/main.py`,
`admin_api/routes/settings.py`, `admin_api/routes/auth.py`, `admin_api/routes/people.py`,
`admin_api/routes/tool_contexts.py`, `gateway/gateway.py`, `billing/generate_invoice.py`,
`billing/finalize_invoice.py`.

## Proposed approach
1. `./.venv/bin/ruff check . --fix` for `I001`/`F401`; **review the F401 removals** (don't drop
   an import with an import-time side effect); fix the single `F841` by hand.
2. Do **not** touch `F821` (story-23) — keep `--select` scoped or fix, re-run, and leave the 3
   F821 for C1.
3. Verify `./.venv/bin/ruff check .` is clean **except** the 3 F821, and green entirely once
   story-23 lands.

## Dependencies / coordination (rule 8)
- Several affected files (`admin_api/routes/*`, `gateway.py`) currently have **C1's uncommitted
  work**. Running `--fix` now would clobber their working tree. **Do not start until C1's
  uncommitted changes in those files are committed/merged.**
- `gateway.py` overlaps [[story-23]] — sequence the two so they don't conflict in that file.

## Acceptance
- `./.venv/bin/ruff check .` reports **0** `I001`/`F401`/`F841` (only the 3 F821 may remain,
  pending story-23; 0 once it lands).
- No behavior change (imports with side effects preserved); focused + full `pytest` green.
- Gate: `brooks-review` + `brooks-audit` clean, then focused + full `ruff`/`pytest` green
  (AGENTS.md rules 2/9), on a `story-24-…` work branch (rule 10).

## Review
_(fill before commit/push: brooks-review + brooks-audit scores/Criticals, then focused + full
ruff/pytest green.)_

## Notes
Sibling: [[story-23]] (the F821 real bugs, owned by C1).
