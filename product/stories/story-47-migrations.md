# Story 47 - Migrations framework + schema_init (replace admin schema-on-startup)

## Status
**Done (branch `story-47-migrations`).** P1 of the blueprint adoption backlog.

## Goal
Adopt the blueprint's **migrations + schema_init** model for the admin schema: forward-only,
tracked, repair-safe — replacing "read `schema.sql` and execute on every startup".

## Scope (admin-side; gateway schema left as-is — follow-up)
- `migrations/0001_baseline.sql` — the admin schema moved verbatim (all `IF NOT EXISTS`), now the
  first forward-only migration.
- `admin_api/schema_init.py` — runner: ensures a `schema_migrations(version, applied_at)` table,
  applies `migrations/*.sql` not yet recorded (each in its own transaction: statements + tracking
  insert), returns applied versions. `db` import is **lazy** (module stays importable in CI without
  psycopg2). Pure `all_migrations()`/`pending()` for tests.
- `admin_api/main.py` lifespan → `run_migrations()` (was inline `_apply_schema()` reading `schema.sql`;
  `Db` import dropped from main.py).
- `tests/test_migrations.py` — baseline present/first, `pending()` filtering, ordering (no DB needed).
- **Out of scope:** gateway's own `gateway/sql/schema.sql` (applied by `gwdb.apply_schema`) — a noted
  follow-up to consolidate into `migrations/`.

## Acceptance
- Runner applies the baseline idempotently (no-op on the existing live DB, recorded in
  `schema_migrations`; second run = `[]`); admin app imports (69 routes); full ruff + pytest green.
- Merged to `main` after the gate.

## Review
Validated against the live DB: first run `['0001_baseline.sql']`, second run `[]`, `schema_migrations`
row present. Baseline is `IF NOT EXISTS` so the existing DB is untouched. Admin imports OK. Lazy `db`
import keeps CI green (no psycopg2 in CI). Full ruff clean, pytest green. No 🔴. **Done.**
