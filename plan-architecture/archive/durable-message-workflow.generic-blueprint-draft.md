# Durable Message Workflow

This is the short agent-facing guide for `<AGENT_NAME>`'s durable user-message
workflow. Use it when planning or changing any user-facing channel, webhook,
adapter, runtime handoff, outbound send path, Activity Log surface, or retry
behavior.

The durable workflow exists because channel calls can time out while the
runtime is still working. A user message must not disappear just because one
HTTP caller timed out. The database-backed `requests`, `channel_events`, and
`work_items` rows are the workflow source of truth.

## Non-Negotiable Rule

Every user-facing inbound request that can reach `<AGENT_RUNTIME>` must have one
internal `request_id` from `requests.id` and one durable `work_items` row before
long-running Hermes/runtime work begins.

Channel adapters and webhooks may do provider intake, parsing, request creation,
provider-event idempotency, and durable enqueue/update work. They must not wait
inline for Hermes/runtime to produce the final user reply as the normal channel
path.

Runtime and provider calls still need ordinary I/O timeouts. Those timeouts are
attempt results on the same work item. They must move the item to
`failed_retryable`, `failed_needs_review`, or an equivalent explicit state, or
attach a late runtime result to the same work item when possible. They must not
silently drop a reply, create a disconnected duplicate request, or make provider
IDs the workflow identity.

## Current Path

```text
channel provider
  -> channel adapter or webhook
  -> create or preserve requests.id
  -> claim provider event / idempotency state in channel_events
  -> `<ADMIN_API>` durable intake (POST /messages)
  -> work_items row
  -> workflow worker claim
  -> people governance, safety, and inbound audit
  -> Hermes runtime bridge when can_converse=true
  -> save reply_ready when `<AGENT_NAME>` produces a reply
  -> channel-specific outbound send stage
  -> completed / failed_retryable / failed_needs_review
  -> channel provider
```

`POST /messages` is the canonical gateway boundary. The worker-owned gateway flow
checks Postgres-backed `people` and `person_identities`, writes audit events, and
only hands approved conversation to the runtime. `can_converse` controls whether
`<AGENT_NAME>` may reply; `can_influence` controls whether the exchange may shape memory.

Direct channel-to-runtime paths are not production architecture. Inline
adapter-to-runtime or gateway-to-runtime waits outside the durable worker path
are migration bugs unless an explicitly approved realtime exception says
otherwise.

## Identity Model

The internal `request_id` is the stable workflow identity. It is the
DB-generated `requests.id`, and it must pass through:

- `POST /messages`
- `work_items`
- governance, safety, audit, and job timing logs
- runtime bridge logs
- workflow worker responses
- outbound send logs
- admin Activity Logs and Activity Detail views

Provider message IDs, provider thread IDs, channel event IDs, phone call IDs,
Google Chat resource names, Telegram message IDs, Gmail message IDs, Discord
message IDs, and Hermes session IDs are metadata only. They must not replace
`request_id` as the workflow identity.

Provider idempotency belongs in `channel_events` or the equivalent provider
event claim surface. Work execution belongs in `work_items`. Keep those concepts
separate so provider redelivery cannot create a second disconnected request and
workflow retry cannot accidentally mark a provider event as successfully sent.

## Worker Ownership

The durable workflow worker owns the long-running stages:

- governance and safety execution
- Hermes/runtime handoff
- reply persistence
- outbound send
- retry or review state transitions

Current implementation notes:

- `<ADMIN_API>.work_items.WorkItemStore` owns durable enqueue, claim, status, and
  schema behavior.
- `<AGENT_RUNTIME>.workflow_worker.DurableWorkflowWorker` claims work and runs the
  worker-owned flow.
- `ready`, `failed_retryable`, and `reply_ready` rows are claimable.
- `reply_ready` rows skip runtime and go straight to outbound send.
- Email and Telegram have worker-callable outbound senders today.
- If a channel has a saved reply but no worker-callable sender, the item must
  move to `failed_needs_review` with a non-secret error summary instead of
  losing the reply.

## Status Model

The workflow uses these durable statuses:

- `ready`: accepted and eligible for worker processing.
- `processing`: claimed by a worker for governance, safety, runtime, or related
  processing.
- `waiting_for_confirmation`: parked because safety requires user or admin
  confirmation before continuing.
- `reply_ready`: `<AGENT_NAME>` produced a reply and it has been saved before outbound
  provider delivery.
- `completed`: workflow reached a terminal success or no-reply terminal state.
- `failed_retryable`: the same request should be retried later.
- `failed_needs_review`: a human/operator must inspect or repair the request.

`reply_ready` is the durable boundary before outbound send. If runtime succeeds
but provider send fails, retry outbound send without rerunning runtime. If a
worker reclaims a `failed_retryable` item that already has non-empty
`reply_text`, it should resume at outbound send, not regenerate the reply.

## Worker Defaults

Use these defaults unless staging testing shows they should be raised:

```text
AGENT_WORKER_CONCURRENCY=3
AGENT_WORKER_BATCH_SIZE=10
AGENT_WORKER_POLL_SECONDS=2
AGENT_WORKER_LOCK_SECONDS=300
AGENT_WORKER_RETRY_SECONDS=30
```

`AGENT_WORKER_CONCURRENCY` controls how many work items are processed at the same
time inside the running worker process.

`AGENT_WORKER_BATCH_SIZE` controls how many rows the worker claims per poll. It
can be larger than concurrency so the worker can keep itself fed without running
every claimed item at once.

`AGENT_WORKER_POLL_SECONDS` controls how often the worker checks for ready work
when no work is available.

`AGENT_WORKER_LOCK_SECONDS` controls how long a claimed work item stays locked
before another worker may reclaim it.

`AGENT_WORKER_RETRY_SECONDS` controls the default delay before retryable failures
become eligible again.

## Scaling Model

The worker claims rows with PostgreSQL row locking and `SKIP LOCKED`. Multiple
workers can look at the same durable table without processing the same work item
twice. If one worker has already locked a row, another worker skips it and claims
a different eligible row.

The current behavior is automatic concurrency inside one worker process. It does
not automatically add more containers or OS processes based on load. If `<AGENT_NAME>`
later needs horizontal scaling, Docker/staging/prod can run more worker
processes without changing the database coordination model.

Do not add Temporal, Celery, Redis, Pub/Sub, or another queue system to this path
unless a future architecture decision explicitly approves that migration. The
current durable bucket is Postgres-backed.

## Channel Expectations

Email/Gmail and Telegram currently use durable work items for reactive inbound
messages and outbound replies.

Discord, Google Chat, phone, meetings, and future governed channels must
converge on this same durable bucket pattern before they are considered
production-ready. Any inline channel path that blocks on Hermes/runtime for the
final user reply is a migration bug unless it has a documented realtime
exception.

Phone is the known low-latency exception shape. Realtime voice may need bounded
provider waits and fallback behavior, but it still must define how request
identity, governance, audit, runtime results, user-visible delivery, and retry or
review state are preserved.

## Safety And Secrets

The workflow must keep the `<AGENT_NAME>` governance boundary. Channel adapters
still enter through `<ADMIN_API>`, and the worker must not create a direct
channel-to-Hermes path that bypasses people governance, safety checks, request
IDs, work item state, or audit logging.

Workflow metadata must not store or log:

- OAuth tokens
- API keys
- channel secret YAML
- session cookies
- fully expanded environment/config values
- attachment bytes
- base64 payloads
- raw secret-bearing files

Generic metadata should stay limited to IDs, counts, statuses, stage names,
non-secret provider references, and non-secret timing/error summaries.

## Change Checklist For Agents

When planning or changing a user-facing channel workflow, explicitly answer:

- Where is `requests.id` created or preserved?
- Where is provider event idempotency claimed?
- Where is the `work_items` row enqueued or updated?
- What fields preserve channel, provider, sender, message, and thread identity?
- Which component owns governance, safety, runtime handoff, and outbound send?
- What happens if runtime times out?
- What happens if provider outbound send times out after `reply_ready`?
- How are duplicate provider events prevented from causing duplicate replies?
- Which states appear in Activity Logs and Activity Detail?
- What audit/log fields are written, and how are secrets redacted?
- What local and staging smoke tests prove the workflow does not depend on an
  inline request staying open?

If the answer depends on prompts, filename conventions, inferred session IDs, or
provider-specific IDs as the primary workflow identity, the plan is not complete.

## Related Repo Docs

- `product/product-decisions/current-architecture.md`: current message path and
  architecture.
- `product/product-decisions/architecture-decisions.md`: durable work bucket
  decision and timeout rationale.
- `product/agent-feature-dev-process.md`: agent-facing implementation process
  and durable workflow rule.
- `ops/brain-whitelabel.md`: broader operational/system explanation.
- `product/stories/archive/story120-durable-request-workflow-all-channels.md`:
  Story 120 implementation history and staging verification.

## External Grounding

Last checked: 2026-08-08.

The current implementation is Postgres-backed, but the design follows common
durable workflow principles:

- PostgreSQL documents `FOR UPDATE ... SKIP LOCKED` as useful for queue-like
  tables with multiple consumers:
  <https://www.postgresql.org/docs/current/sql-select.html>.
- Temporal describes durable workflow execution as preserving workflow history
  so work can continue after failures: <https://docs.temporal.io/workflows>.
- Celery documents retry state and retry delays for recoverable task failures:
  <https://docs.celeryq.dev/en/stable/userguide/tasks.html>.

These are grounding references, not installed dependencies for this workflow.
