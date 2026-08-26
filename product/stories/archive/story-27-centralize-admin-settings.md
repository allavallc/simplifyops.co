# Story 27 - Centralize `admin_settings` access (kill duplicated cap/timezone reads)

## Status
**Proposed.** Addresses the R3 Knowledge Duplication / Information Leakage 🟡 finding from the
2026-08-22 architecture audit.

## Problem
The decision "read an `admin_settings` key, fall back to a default literal" is expressed in
multiple independent places, with the default `100` repeated verbatim:

| Location | Key |
|---|---|
| `gateway/gateway.py:200` (`get_session_message_cap`) | `session_message_cap` (default 100) |
| `admin_api/main.py:403–405` | `session_message_cap` (default 100) |
| `admin_api/routes/settings.py` (L80, L132–134, L200) | `session_message_cap` (default 100) |
| `gateway/gateway.py:599` | `default_timezone` (same pattern) |

Changing a default or key requires coordinated edits across two services and four+ sites, and they
can silently drift (gateway enforces one value while the admin UI reports another).

## Proposed approach
1. **Within `admin_api`** — add one accessor, `get_setting(key, default)` (in `db.py` or a small
   `settings_store`), and route every `admin_settings` read through it. Define each default **once**
   as a named constant; remove the repeated `100` literals from `main.py` and `routes/settings.py`.
2. **In `gateway`** — since it's a separate service (own DB access), keep its own single accessor
   but define the default as a **named constant** (not a bare literal), documented as mirroring the
   admin contract. (Cross-service dedup beyond a shared constant is out of scope — separate
   deployables.)
3. Same treatment for `default_timezone`.

## Acceptance
- The `100` cap default and the `session_message_cap` key literal each appear **once per service**,
  behind a named accessor/constant; `default_timezone` likewise.
- No behavior change (same values read/written); `pytest` green.
- Gate: `brooks-review` + `brooks-audit` clean, then focused + full `ruff`/`pytest`, on a
  `story-27-…` work branch (rule 10).

## Review
_(fill before commit/push: brooks-review + brooks-audit scores/Criticals, then focused + full
ruff/pytest green.)_

## Notes
Touches `gateway.py` — sequence with [[story-26-decompose-gateway-module]] (the accessor lands in
`gateway/sessions.py` if that split goes first).
