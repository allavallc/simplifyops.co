# Story 26 - Decompose the `gateway.py` god-module into a package

## Status
**DONE (local, verified live — 2026-08-25).** Resolves the 🔴 **Critical** (R1; also R2 Divergent
Change, R5 missing seams). `gateway.py` **1181 → 50 lines** (pure composition root + `main()`),
decomposed into 9 single-responsibility modules: `gwdb` (DB), `intake` (request id/enqueue/prompt),
`governance` (people lookups + unknown-sender queue + person context), `sessions` (history + Hermes
session mappings + cap), `tool_context` (MCP tokens), **`hermes_client` (the Hermes adapter —
protected rule 10)**, `worker` (`DurableWorkflowWorker`), `telegram` (adapter + `send_outbound`),
`internal_server` (`/internal/reply`). All ruff-clean, all import cleanly (no cycles), gateway service
restarted clean each increment (NRestarts=0; worker + adapter + internal server all start). The Hermes
boundary is now one seam — the 0.20.5 upgrade validated it.

## Problem
`gateway/gateway.py` is **1,183 lines**, 40+ functions and 3 classes, carrying ~8 unrelated
responsibilities in one file:
- DB access + schema (`get_db_conn`, `apply_schema`)
- session history / session mapping / session cap
- prompt building + governance
- `call_hermes` (streaming, ~170 lines by itself)
- tool-context minting + person context
- `DurableWorkflowWorker` (retry/dead-letter)
- internal `HTTPServer` (`InternalHandler`)
- the full Telegram adapter (get_updates/send/typing/file-download/transcription/dead-letter/`main`)

Its responsibility cannot be stated in one sentence. Every gateway concern shares one edit surface
and one blast radius on the system's busiest path, and none of it can be unit-tested without a live
DB + network (no seams).

## Proposed approach (structural — needs approval before coding, rule 3)
Split into a `gateway/` package with one responsibility per module, keeping behavior identical:
- `gateway/db.py` — connection factory + `apply_schema`
- `gateway/sessions.py` — history, session mapping, session-cap read
- `gateway/governance.py` — `governance_check`, person/tool context
- `gateway/hermes_client.py` — `call_hermes` + streaming + session count
- `gateway/worker.py` — `DurableWorkflowWorker`
- `gateway/internal_server.py` — `InternalHandler` / `start_internal_server`
- `gateway/telegram.py` — Telegram adapter (`_tg_*`, updates, attachments, dead-letter)
- `gateway/gateway.py` — thin composition root: `main()` + wiring only
- **Introduce seams** — pass a DB connection factory and the Hermes/HTTP client into
  `DurableWorkflowWorker` and the adapter instead of module-level globals, so they can be doubled.

Depends on / coordinates with [[story-28-repo-local-logging]] (both touch gateway imports) —
sequence to avoid churn.

## Acceptance
- No single gateway module carries more than one statable responsibility; `gateway.py` is
  wiring-only.
- Message flow behavior unchanged (Telegram → work_items → worker → Hermes → send) — verified
  against `product/product-decisions/current-architecture.md` message flow.
- New unit tests exercise `worker` and `governance` with doubled DB/HTTP seams.
- Gate: `brooks-review` + `brooks-audit` clean (Critical resolved), then focused + full
  `ruff`/`pytest`, on a `story-26-…` work branch (rule 10). `graphify update .` re-run.

## Review
_(fill before commit/push: brooks-review + brooks-audit scores/Criticals, then focused + full
ruff/pytest green.)_

## Notes
Coordinate on shared infra (gateway service) per rule 8 before starting.
