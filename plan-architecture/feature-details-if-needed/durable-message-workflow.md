# Boundary contract — Durable message workflow

The path a user message travels from a channel adapter to a delivered reply. This is the system's
core durable boundary: every inbound message becomes a persisted `requests` row and a `work_items`
row, and progress is a state machine in Postgres — not in-memory. A crash at any point resumes from
the last committed state; nothing is lost and nothing is silently re-run past its retry budget.

Documented per the rule-15 contract checklist (`AGENTS.md`). Grounded in
`admin_api/routes/messages.py`, `gateway/worker.py`, `gateway/intake.py`.

> **Build-spec doc** (companion to the law [`agents-whitelabel-instructions.md`](../agents-whitelabel-instructions.md)). Last
> relocated to `plan-architecture/` on 2026-08-27. **Approved divergence from the blueprint:** the
> blueprint routes the runtime handoff through a private `POST /runtime/messages` bridge (:8090) fronted
> by a supervisor; **this repo** hands off directly via the `gateway`/`hermes_client` adapter (no bridge
> yet) and runs natively (no Docker) — a recorded product-decision (2026-08-26), not drift.

## Overview

```
channel adapter (gateway/telegram.py)
  → POST /messages           [admin_api/routes/messages.py]  — governed intake, returns 202
      → requests (row)                                       — durable inbound record
      → channel_events (row, if provider_event_id)           — dedup claim
      → work_items(status='ready', payload)                  — durable unit of work
  → DurableWorkflowWorker     [gateway/worker.py]             — claims + processes
      → get_person_context → build_prompt → call_hermes      — runtime handoff
      → work_items(status='reply_ready', reply_text)         — reply persisted BEFORE send
      → send_outbound                                        — channel delivery
      → work_items(status='completed')
```

## Contract: `POST /messages` (intake)

| Field | Value |
|---|---|
| Caller / callee | channel adapter (e.g. `gateway/telegram.py`) → admin API `POST /messages` |
| Route | `POST /messages` (admin control plane, :3000) |
| In schema | `MessagePayload`: `channel`, `provider?`, `from_id`, `from_name?`, `chat_id`, `message_text`, `provider_event_id?`, `raw?` |
| Out schema | `202` + `{request_id, status, work_item_id?}` where `status ∈ {accepted, queued_for_review, declined, duplicate}` |
| Persisted state | `requests` (always), `channel_events` (if `provider_event_id`), `work_items` (approved only), `contact_requests` (unknown sender) |
| `request_id` | Minted server-side per call (`uuid4().hex`); the correlation key across all tables and logs |
| Idempotency | `channel_events(channel, provider_event_id)` unique — a re-delivered provider event returns `duplicate`, no second work item |
| Timeout / retry | **None at intake** — returns `202` immediately, never waits for the runtime |
| Credential owner | none (internal call, loopback) |
| Delivery owner | n/a (intake does not send) |
| Status mapping | approved→`accepted`; unknown sender→`queued_for_review`; blocked/`can_converse=false`→`declined`; dup event→`duplicate` |
| Audit fields | `governance_approved` / `governance_blocked` / `governance_declined` / `governance_unknown_sender` via `log_audit` |
| Redaction | message text is stored (governed DB); not logged verbatim at INFO |

Governance is resolved via `person_identities → people` (protected rule 9: `people_service` is the
single source of truth). Only `status='allowed'` + `can_converse=true` senders are enqueued; the
sender's `authority` and `can_influence` are snapshotted into `work_items.payload` at intake so the
worker never re-reads governance.

## Contract: worker runtime handoff (`work_items` → Hermes → outbound)

| Field | Value |
|---|---|
| Caller / callee | `DurableWorkflowWorker` → `hermes_client.call_hermes` (the sole runtime adapter, protected rule 10) → `telegram.send_outbound` |
| Claim | `SELECT … FOR UPDATE OF w SKIP LOCKED LIMIT concurrency`, then set `processing` + `locked_until` — safe for multiple workers |
| Eligible states | `ready`, `failed_retryable`, `reply_ready`, or `processing` whose `locked_until` has expired (crash recovery) |
| Persisted state | `work_items.status`, `attempt_count`, `reply_text`, `error_summary`, `locked_until`, `retry_after` |
| `request_id` | Carried from intake; every worker log line keys on `item_id` + `request_id` |
| Idempotency | reply is saved (`reply_ready`) **before** outbound; a failed send retries **outbound only**, never re-runs Hermes |
| Timeout | `WORKER_LOCK_SECONDS` (default 300) lock; expired locks are reclaimable |
| Retry | up to `WORKER_MAX_ATTEMPTS` (3); `failed_retryable` sets `retry_after = now()+30s`; exhausted → `failed_needs_review` |
| Credential owner | runtime API auth owned by `hermes_client` (`_agent_api_headers`) |
| Delivery owner | `telegram.send_outbound` (channel-specific); returns ok/fail, mapped to `completed`/retry |
| Status mapping | success→`completed`; runtime `None`→retry or `failed_needs_review`; send fail→retry or `failed_needs_review` |
| Audit / alert | `failed_needs_review` sends a Telegram alert to `ADMIN_TELEGRAM_CHAT_ID` (`_notify_failed_needs_review`) |
| Redaction | reply length + timing logged, not the reply body |

### `work_items.status` state machine

```
ready ─┐
       ├─► processing ─► reply_ready ─► completed
reply_ready ─┘              │
                            ├─► (send fail, attempt<3) failed_retryable ─► processing …
                            └─► (attempt≥3)            failed_needs_review  (Telegram alert)
```

`reply_ready` is the crucial durability seam: once the runtime has produced a reply it is committed
before any delivery attempt, so a delivery crash costs a resend, never a re-generation (and never a
second charge against the model).

## Invariants (do not break without an approved story)

- Intake returns `202` immediately — the runtime is **never** on the request path (protected rule 1).
- The reply is persisted (`reply_ready`) **before** the first send attempt.
- Governance is evaluated once, at intake, and snapshotted into `payload` — the worker does not
  re-decide who may converse.
- Hermes is reached **only** through `hermes_client` (protected rule 10).
- `channel_events(channel, provider_event_id)` is the single dedup point — see
  [`channel-message-tracking.md`](channel-message-tracking.md).
