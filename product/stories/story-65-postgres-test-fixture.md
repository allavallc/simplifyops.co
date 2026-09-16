# story-65 — Postgres test fixture for the knowledge DB layer

## Status
**Done.** 🧩 small / test-infra. Locks in automated coverage for the DB-layer authority
filters that story-64 C2 could only verify live (the repo has no live-Postgres test harness). Follow-up
to [[story-64]] (see its C2 review — "Coverage Illusion" accepted-by-design, deferred to a fixture story).

## Problem
`knowledge_store.get_visible_by_slug` / `search_visible` / `list_docs` and `tool_context_store.resolve`
carry the authorization-critical SQL (authority window + `status='active'` + token expiry). Today these
are exercised only by a throwaway script at deploy time. A wrong predicate = an authority leak with no
red test. The pure helpers (`search_matches`, `clamp_max_results`) and the connector governance flow
(monkeypatched) are already covered; this story covers the **SQL layer** against a real database.

## Constraints (verified)
- Local dev + this Pi have Postgres on the unix socket; **CI is native (no Docker)** per `ci.yml`.
- The DB role `pi` **cannot `CREATE DATABASE`** (`rolcreatedb=f`) — a throwaway *database* is out.
- `pi` **can** create/drop **schemas** in `whitelist_app`, and `search_path` is settable via the DSN
  (`options=-csearch_path=...`) — so a throwaway **schema** gives full isolation with no privilege change
  and zero pollution of the real tables.

## Plan (pending decisions D1/D2 below)
- **`tests/conftest.py`** — a session-scoped `knowledge_db` fixture that:
  1. points `GATEWAY_DB_DSN` at `whitelist_app` with `search_path=ktest_<pid>,public` (set before
     `db.init_pool()`),
  2. `CREATE SCHEMA ktest_<pid>` and creates the three needed tables (`knowledge_documents`,
     `knowledge_document_versions`, `tool_contexts`) from the committed DDL,
  3. yields, then `DROP SCHEMA ... CASCADE` on teardown.
  A function-scoped `TRUNCATE` keeps tests independent. If Postgres is unreachable, the fixture calls
  `pytest.skip` (so pure tests still run everywhere).
- **`tests/test_knowledge_db.py`** — real-DB tests mirroring the deploy verification: token
  resolve (valid/expired/unknown); authority matrix for list/read/search (contact→super_admin);
  archived excluded; invisible slug == missing (same not-found); search never leaks restricted
  docs/snippets; `create → get_visible_by_slug → search_visible` round-trips through the shared service.
- **DDL source:** reuse `migrations/0002_knowledge.sql` for the knowledge tables; add the `tool_contexts`
  DDL. Keep one authoritative DDL — the fixture applies the same statements, not a hand-retyped copy.
- Full gate (brooks-review + brooks-audit, focused + full ruff/pytest). No production-code change is
  expected unless D1 = "inject connection".

## Key decisions for approval
- **D1 — isolation strategy:**
  - **(rec) Dedicated throwaway schema** `ktest_<pid>` + `search_path` DSN — full isolation, no prod
    pollution, no privilege change; ~1 fixture of DDL setup/teardown.
  - **Seed-and-delete on the real tables** — simplest, but transiently writes to prod `knowledge_documents`
    and risks leftover rows if a test aborts before teardown.
  - **Refactor the store to accept an injected connection** + rollback-per-test — cleanest seam, but
    changes production function signatures (against "minimal code"; wider blast radius).
- **D2 — CI:**
  - **(rec) Auto-skip when no DB is reachable** — DB tests run locally + on this Pi; CI keeps running the
    pure suite unchanged (respects the current native, no-Docker CI). Coverage exists where a DB exists.
  - **Add a Postgres service to CI now** — DB tests also run in GitHub Actions; changes CI infra
    (a service container) and departs from the "native, no Docker" note in `ci.yml`.

## Acceptance
Real-DB tests pass locally + on the Pi; pure suite + CI unaffected (skips cleanly with no DB); the
authority matrix, archived exclusion, missing==invisible, and no-leak search are all asserted against
Postgres. No leftover `ktest_*` schema after a run.

## Decisions taken
- **D1 = throwaway schema** (approved), realized as **`LIKE public.x INCLUDING ALL` clones** rather than
  replaying migrations: the app schema is fragmented across admin/gateway/migration files with no clean
  "build from scratch" entrypoint, and `LIKE` omits foreign keys, so `tool_contexts` clones without the
  `people` table it references. The live schema is the most authoritative DDL source.
- **D2 = auto-skip when no DB reachable** (approved): `psycopg2` connect probe; CI (no Postgres) skips
  the DB tests and runs the pure suite unchanged. `psycopg2-binary` added to `requirements-dev`.

## Review — story-65
Built: `tests/conftest.py` (`knowledge_db` session fixture → throwaway `ktest_<pid>` schema of cloned
tables, `search_path`-scoped, dropped on teardown; `kdb` per-test truncation; skip when unreachable) +
`tests/test_knowledge_db.py` (7 real-DB tests: token resolve/expiry; list/read/search authority window +
active-only; missing==invisible; no restricted leak; category filter; create→read round-trip).

**Review:** brooks-review + brooks-audit on the rebased branch. One 🟡 — the fixture mutated `db`
module globals (`DSN`, `_pool`) without fully reverting — **fixed** (original `DSN` saved/restored in
teardown). 🟢s: minor connect duplication (intentional) and tests depending on live tables to clone
from (intentional, skip-guarded); a positive testability-seam note. No 🔴. **Gate:** rebased on `main`;
full ruff clean; pytest 90 green (7 new); story-summary check OK; no leftover `ktest_*` schema. Also
regenerated `product/stories-archive.md`, which the story-64 archive commit had left stale.
