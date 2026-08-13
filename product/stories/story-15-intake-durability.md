# Story 15 - Telegram intake durability (stop dropping messages on admin outage)

## Status
✅ Built 2026-08-12 (approved by Anthony). Live in gateway.
Acceptance test that needs a real inbound Telegram message (kill-admin → send →
recover) is left for Anthony to trigger — the gateway must never be sent test
messages by Claude (James off-limits). Static correctness verified.
Raised by the concurrent LLM working the box (2026-08-11); verified against code.

### What was built
- `channel_dead_letter` table in `gateway/sql/schema.sql` (gateway-owned; the
  admin schema does not own intake tables, so no mirror).
- `telegram_adapter()` rewritten: offset advances **only** on a terminal outcome.
- `_handle_update()` returns `terminal`/`retryable`; 2xx → terminal, 422 →
  dead-letter + terminal, network/5xx → retryable, unhandled exception → poison →
  dead-letter + terminal.
- Bounded exponential backoff (`INTAKE_BACKOFF_MIN/MAX_SECONDS`, 1→30s) re-polls
  the same un-advanced offset; idempotent replay via `channel_events` UNIQUE.

## Problem
In `gateway/gateway.py::telegram_adapter()` the Telegram long-poll offset is
advanced **before** the message is safely handed off:

```python
for update in updates:
    offset = update["update_id"] + 1        # line 988 — advances immediately
    ...
    r = requests.post(f"{ADMIN_API_URL}/messages", ...)   # line 1018 — actual intake
    if r.ok: ...
    else:  log.error("POST /messages failed ...")          # line 1041 — only logs
    except Exception:  log.error("POST /messages error ...")# line 1043 — only logs
```

Because `offset` is already past the update, a failed/blocked intake is **not**
redelivered by Telegram — the inbound message is silently and permanently lost.

### When it bites
Any time the admin API can't accept intake while the gateway is polling:
- admin restart / crash / deploy window (uvicorn not yet bound)
- transient 5xx or connection refused / timeout
- the exact boot race the `ExecStartPre` readiness gate mitigates — but that gate
  only covers **startup**, not mid-operation outages.

## Why it's safe to fix properly
Intake is **idempotent**: `channel_events` has `UNIQUE(channel, provider_event_id)`
and `provider_event_id = "{message_id}:{chat_id}"`. Re-fetching and re-POSTing
the same update returns `status: "duplicate"` (already handled at line 1034) — so
retrying the same offset cannot double-enqueue.

## Proposed approach (needs approval — control-flow change)
Advance the offset only on a **definitive** outcome; re-fetch the same update on
retryable failure; never blind-retry a poison message.

Per update:
- **Terminal success** — HTTP 2xx with a known status (`accepted`, `duplicate`,
  `queued_for_review`, `declined`): advance offset.
- **Terminal reject** — HTTP 422 (malformed/unprocessable, will never succeed):
  **dead-letter** it (persist the raw update + reason), then advance — so one bad
  message can't wedge the whole channel.
- **Retryable** — connection refused / timeout / 5xx: do **not** advance; break the
  batch and re-poll the same offset with bounded exponential backoff (e.g.
  1→2→4→8s, cap ~30s). The readiness gate + admin `Restart=on-failure` mean the
  admin returns within a bounded window and the same update is re-delivered.

### Dead-letter sink (resolved — Anthony, 2026-08-12)
New **`channel_dead_letter`** table: raw update JSON, reason, timestamp (plus
channel + provider_event_id for correlation). Inspectable later in admin
Inbox/Activity; matches the brain-doc "nothing silently dropped" posture. Add to
`gateway/sql/schema.sql` (+ mirror in `admin_api/schema.sql`).

### Guardrails
- Bound total backoff so a permanently-down admin doesn't freeze Telegram polling
  forever (after cap, log LOUD + optionally alert, keep the update unacked so it's
  re-tried on recovery — do not drop).
- Keep the existing typing indicator only on `accepted`.

## Acceptance
- Kill the admin API, send a Telegram message, bring admin back → the message is
  intake'd on recovery (not lost).
- A forced 422 lands in the dead-letter sink and polling continues.
- No double-enqueue when the same update is re-fetched (relies on idempotent
  `provider_event_id`).
- Normal-path latency unchanged.

## Key Files
- `gateway/gateway.py` — `telegram_adapter()` (~980-1049), `_tg_get_updates()` (~842)
- `gateway/sql/schema.sql` — `channel_events` (idempotency key); dead-letter table if chosen
- Admin Inbox/Activity — surfacing dead-letters (follow-up, out of scope here)

## Out of scope
- Async agent-turn dispatch (separate concern — see the sync→async migration issue).
- Retry semantics of the durable worker itself (already ≤3 → failed_needs_review).
