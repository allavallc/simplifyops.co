# Story 14 - Person `timezone` column (fix silent person-context loss)

## Status
✅ Built 2026-08-12 (approved by Anthony; default EST). Live.

### What was built
- `people.timezone` column (`admin_api/schema.sql` idempotent ALTER; applied live).
- Org default `default_timezone = America/New_York` seeded in `admin_settings`
  (`gateway/sql/schema.sql`).
- `get_person_context()` resolves person → org default → UTC via COALESCE, in one
  query — no more `column p.timezone does not exist`; value reaches `system_message`
  + `tool_contexts.timezone`.
- People form + detail view show/edit per-person timezone (blank → inherits).
- Settings → **Organization** section edits the org default (GET/PATCH
  `/api/admin/settings/default-timezone`, IANA-validated via `zoneinfo`, audited).
  Applied **live** — gateway reads it per lookup, no runtime restart.
- Verified: a person with no tz set resolves to `America/New_York`.

## Problem
`get_person_context()` in `gateway/gateway.py` (~line 556) runs:

```sql
SELECT p.id, p.person_email, p.timezone
FROM people p ... WHERE ...
```

but the `people` table has **no `timezone` column**. The query raises
`column p.timezone does not exist`, which is caught by the surrounding
`try/except` and only logged as a WARNING. The failure is therefore silent, and
it happens on **every inbound message**, not just occasionally.

### Blast radius (why this is more than a cosmetic warning)
Because the whole `SELECT` throws, `get_person_context()` returns an empty dict,
so for every message the runtime handoff loses:
- `primary_email` — the person's identity passed to the agent
- `timezone` — used to build the `system_message` (`gateway.py:405-406`) and
  written into the `tool_contexts` row (`gateway.py:530-537`)

`tool_contexts.timezone` is `NOT NULL DEFAULT 'UTC'`, and the insert already
falls back to `person_ctx.get("timezone", "UTC")`, so tokens still mint — but
every person is silently treated as UTC with no email context. This degrades
governance/context quality for James on 100% of messages.

## Root cause
Schema/query drift. Story 7 (Tool Contexts) added `get_person_context()` reading
`p.timezone` and a `tool_contexts.timezone` column, but the `timezone` attribute
was never added to the `people` table. The brain-whitelabel doc lists `timezone`
as a first-class person-record field (person records: "`timezone`, `notes`") and
threads it through tool context, automations, and schedule behavior — so the
intended fix is to **add the column**, not to drop it from the query.

## Goal
Make person context resolve cleanly, with `timezone` as a real, editable
per-person attribute that flows person → `system_message` → `tool_contexts`,
consistent with the brain-whitelabel person-record model.

## Approach (data-model decision resolved — Anthony, 2026-08-12)
**Org-wide default timezone = EST (`America/New_York`)**; a person with no
timezone set inherits the org default (not blanket UTC).

1. **Schema:** `ALTER TABLE people ADD COLUMN IF NOT EXISTS timezone text` —
   nullable (no column default) so "unset" is distinguishable and inherits the
   org default. Mirror in `admin_api/schema.sql` and `gateway/sql/schema.sql`
   (idempotent `ADD COLUMN IF NOT EXISTS`).
2. **Org default:** store `default_timezone = America/New_York` in
   `admin_settings` (seeded). `get_person_context()` coalesces person `NULL` →
   org default → `UTC` last-resort, instead of the current hardcoded `'UTC'`.
   Surface/edit the org default in Settings (Session Health or a general section).
3. **Resilience (defensive):** in `get_person_context()`, treat a query failure
   as degraded-but-known — return whatever person fields resolve rather than an
   empty dict, so a future missing-column drift can't blank out `primary_email`
   too. (Keep minimal; no new abstractions.)
4. **Admin UI:** surface/edit per-person `timezone` on the People detail/form
   (IANA string, e.g. `America/New_York`); blank → inherits org default (EST).
5. **Backfill:** leave existing rows NULL → they inherit EST. No destructive
   column default.

### Note — "get the timezone part figured out"
Anthony wants the whole timezone story coherent: org default EST, per-person
override, and it must actually reach the agent (`system_message`) and tool
context. Acceptance below covers the end-to-end path, not just the column.

## Acceptance
- No `column p.timezone does not exist` warnings in gateway logs on inbound.
- `get_person_context()` returns `primary_email` + `timezone` for a known sender.
- A person with **no** timezone set resolves to the **org default (EST)**, not UTC.
- Org default is editable in Settings; per-person override editable on People page.
- The resolved timezone reaches the agent `system_message` and `tool_contexts.timezone`.

## Key Files
- `gateway/gateway.py` — `get_person_context()` (~556), `system_message` (~405),
  `create_tool_context()` (~530)
- `admin_api/schema.sql`, `gateway/sql/schema.sql` — `people` table
- `admin_api/` People routes/templates — timezone field

## Notes
- Discovered 2026-08-11 during the project relocation to `/home/pi/projects/simplifyops`.
- Pre-existing; unrelated to the move.
