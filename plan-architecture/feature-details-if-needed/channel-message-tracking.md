# Boundary contract — Channel message tracking & idempotency

How inbound channel events are recorded, de-duplicated, and correlated across the system. This is the
boundary that lets the same physical message arrive twice (provider re-delivery, adapter restart,
long-poll overlap) without producing two replies.

Documented per the rule-15 contract checklist (`AGENTS.md`). Grounded in
`admin_api/routes/messages.py`, `gateway/intake.py`, `admin_api/schema` (`requests`, `channel_events`).

> **Build-spec doc** (companion to the law [`agents-whitelabel-instructions.md`](../agents-whitelabel-instructions.md)). Last
> relocated to `plan-architecture/` on 2026-08-27.

## Tables

| Table | Role |
|---|---|
| `requests` | One row per accepted inbound message. `id` = `request_id` (the correlation key). Columns: `channel`, `provider`, `from_id`, `from_name`, `chat_id`, `message_text`, `created_at`. |
| `channel_events` | Provider-event dedup ledger. `(channel, provider_event_id)` **unique**, plus `request_id` back-reference. A row here means "we have already accepted this provider event." |
| `contact_requests` | Unknown-sender inbox (no work item created) — the parallel track for senders governance does not recognize. |

## Contract: provider-event idempotency

| Field | Value |
|---|---|
| Caller / callee | channel adapter → `POST /messages` → `_enqueue` / `intake.enqueue_message` |
| Key | `(channel, provider_event_id)` — the adapter supplies `provider_event_id` (e.g. Telegram `update_id`/`message_id`) |
| Claim mechanism | `INSERT INTO channel_events …`; a `UniqueViolation` means the event was already accepted → the whole enqueue is rolled back and the caller gets `duplicate` |
| Atomicity | `requests` + `channel_events` + `work_items` are inserted in **one transaction** — either all three exist or none do |
| Missing `provider_event_id` | If the adapter cannot supply one, no dedup row is written and idempotency is **not** guaranteed for that event — adapters should always supply it |
| `request_id` vs `provider_event_id` | `request_id` is minted by us (stable internal key); `provider_event_id` is the external key we dedup on. They are 1:1 for accepted events. |
| Audit | governance decision is logged against `request_id`; duplicates are logged at INFO (`Duplicate provider event …`) and not re-audited |
| Redaction | `provider_event_id` and ids are logged; message text is not logged verbatim |

## Correlation model

```
provider_event_id  ──(dedup)──►  channel_events.request_id
                                        │ 1:1
                                        ▼
request_id  ──►  requests  ──►  work_items.request_id  ──►  logs & audit_log (keyed on request_id)
```

Every log line and audit row downstream keys on `request_id`, so a single message can be traced end
to end: intake → governance decision → work item → runtime handoff → outbound → completion.

## Adapter responsibilities (for new channels)

Any new channel adapter (email, Discord, etc. — backlog story 54) must:

1. Supply a stable `provider_event_id` unique within its `channel` so re-delivery is de-duplicated.
2. Post the normalized `MessagePayload` to `POST /messages` and treat `202` as "accepted for durable
   processing" — **not** as "delivered."
3. Never send a reply itself on the inbound path; delivery is the worker's `send_outbound` step (see
   [`durable-message-workflow.md`](durable-message-workflow.md)).
4. Map channel identity to `from_id` consistently, because governance resolves
   `person_identities(identity_type=channel, normalized_value=from_id)` — the same `from_id` must be
   produced for the same person every time.

## Invariants (do not break without an approved story)

- `(channel, provider_event_id)` is the **single** dedup point — do not add a second dedup scheme.
- The three inbound rows (`requests`, `channel_events`, `work_items`) are written atomically.
- Delivery is never attempted from the intake path; only the worker sends.
