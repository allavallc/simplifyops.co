# Story 49 - Boundary-contract docs

## Status
**Done (branch `story-49-boundary-docs`).** P1 of the blueprint adoption backlog.

## Goal
Document each major internal boundary against the rule-15 contract checklist (`AGENTS.md`), so a
handoff's full contract (caller/callee, route, in/out schema, persisted vs transient state,
`request_id`, idempotency, timeout, retry, credential owner, delivery owner, status mapping, audit,
redaction) is written down where the boundary lives — not rediscovered from code each time.

## Scope (docs only — no code change)
- `ops/durable-message-workflow.md` — the `POST /messages` → `work_items` → `DurableWorkflowWorker` →
  `send_outbound` durable state machine; the `reply_ready` durability seam; worker retry/dead-letter.
- `ops/channel-message-tracking.md` — `requests` / `channel_events` / `contact_requests`;
  `(channel, provider_event_id)` idempotency; `request_id` correlation; new-adapter responsibilities.
- `docs/mcp/agent-mcp-master-doc.md` — the agent↔MCP tool boundary: short-lived hashed tool-context
  tokens (`gateway/tool_context.py` → `GET /api/tool-contexts/{token}`), authority/access rules,
  target repo-owned model. Points at `product-decisions/mcp-setup-and-status.md` for current status
  (does not restate or change it; no MCP action taken).

Each doc is grounded in the actual code (files cited inline) and ends with an **Invariants** section
linking the protected architectural rules.

## Non-goals
- No code, schema, or config changes. No MCP server/connector work (needs Anthony).
- Does not supersede `mcp-setup-and-status.md` (status) — the master doc is the *boundary contract*.

## Acceptance
- Three docs created, each following the rule-15 checklist and citing the source files.
- Full ruff + pytest green (unchanged — docs only); brooks-review/audit clean.
- Merged to `main` after the gate.

## Review
Docs-only diff (4 markdown files, +256). **brooks-review** (`PR Review`): code decay risks R1–R6
don't apply; review reduced to accuracy vs source — each claim verified against the cited files
(`messages.py`, `worker.py`, `intake.py`, `tool_context.py`, `tool_contexts.py`). Quick Test Check
skipped (docs-only, per the skill). **brooks-audit**: no code changed → health score unchanged, no
new boundary violations; docs reinforce protected rules 1/9/10. No 🔴/🟡. Full ruff clean, pytest
12 passed, story-summary sync OK. Rebased on `origin/main` before the gate. **Done.**
