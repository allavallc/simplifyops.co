# Story 17 - Long agent turns: liveness-based streaming (replace the 300s wall-clock kill)

## Status
✅ Built 2026-08-13. All decisions resolved (below). Live in the gateway.
Acceptance requires a real >5min turn (only Anthony can trigger — James off-limits).
Static verification: compiles, gateway loads clean, SSE parsing matches the runtime
event contract in `api_server.py`.

### What was built
- `call_hermes()` now POSTs to `/api/sessions/{id}/chat/stream` with `stream=True`
  and `timeout=(AGENT_API_CONNECT_TIMEOUT=15, AGENT_API_IDLE_TIMEOUT=90)`.
- The read timeout IS the idle/liveness timeout: any event or 30s keepalive resets
  it; 90s of silence → `ReadTimeout` → treated as dead runtime → retry. No wall-clock cap.
- SSE consumer: reply from `assistant.completed.content`, session from
  `assistant.completed`/`run.completed`, `error` → failure, `done` → stop, `:` → keepalive.
- Stale-session 404/410 retry preserved. Legacy sync `/chat` + `AGENT_API_TIMEOUT`
  no longer used by call_hermes (constant left defined, env-overridable).
- Doc note: AGENTS.md message-flow line still says `/chat` — update to `/chat/stream`
  when safe (held to avoid colliding with the other agent's concurrent AGENTS edits).

## Problem
The durable worker calls the runtime **synchronously**:

```python
# gateway/gateway.py:429
requests.post(f"{AGENT_API_URL}/api/sessions/{sid}/chat",
              json={"message": prompt, "system_message": system_message},
              timeout=AGENT_API_TIMEOUT)          # AGENT_API_TIMEOUT = 300s
```

If a legitimate turn (browser work, multi-step tool use) runs past 300s, the
`requests` client times out → `call_hermes` returns `None` → the item becomes
`failed_retryable` and is **re-run from scratch**, even though the agent was fine.
This is what killed work_item #190. A wall-clock cap contradicts the durable-queue
design (turns should complete, not die on a stopwatch).

## Research findings (runtime API — `gateway/platforms/api_server.py`)
The runtime already exposes three chat routes (api_server.py:4066-4068):

| Route | Behavior |
| --- | --- |
| `POST /api/sessions/{id}/chat` | **synchronous** — blocks in `_run_agent` until the whole turn finishes, then returns the final JSON. **No server-side turn timeout** — the 300s is purely the gateway's client-side `requests` timeout. |
| `POST /api/sessions/{id}/chat/stream` | **SSE stream** — same `_run_agent`, but emits progress events as it goes. |
| `POST /v1/chat/completions` | OpenAI-compatible (not relevant here). |

The **stream** endpoint emits (each as `event: <name>\ndata: <json>`):
- `run.started`, `message.started`
- `assistant.delta` (incremental text), `tool.started` / `tool.completed` /
  `tool.failed`, `tool.progress`
- **`assistant.completed`** → `{ content: <final reply>, session_id }`
- `run.completed` → `{ usage, session_id }`, then `error` (on failure), then `done`

Crucially, the server writes a `: keepalive` comment every
**30s** (`CHAT_COMPLETIONS_SSE_KEEPALIVE_SECONDS`) even while the agent is silently
thinking. So **the stream is a continuous liveness signal**: events flow → the
agent is alive; the stream goes silent → the agent/runtime is actually dead.

### Consequence
We do **not** need the concurrent LLM's "dispatch-and-callback via the :3001
server." That would require the runtime to support a webhook callback (it does
not) — i.e. runtime changes. Streaming is already supported and is strictly a
**gateway-side** change. Recommended.

## Proposed approach — Option A (recommended): liveness-based streaming
Migrate `call_hermes()` from the sync `/chat` to `/chat/stream`:
- POST to `/chat/stream`, read the SSE stream line-by-line
  (`requests(..., stream=True)` or `httpx.stream`).
- Reset an **idle timer on every received event** (including `: keepalive`).
- Capture the reply from `assistant.completed.content` (+ `session_id` for
  rotation bookkeeping); treat `error` as failure.
- Replace the wall-clock `AGENT_API_TIMEOUT` with `AGENT_API_IDLE_TIMEOUT` — "no
  events for N seconds ⇒ dead." Since keepalives arrive every 30s, N ≈ 90s (3
  missed keepalives) cleanly distinguishes a hung runtime from a long turn.
- Everything else stays inside the durable worker: still one item at a time, still
  writes `reply_ready`, still retries on genuine failure (`error`/idle/connection
  drop) up to `WORKER_MAX_ATTEMPTS`. No new services, no :3001 changes.

### Option B (not recommended): dispatch-and-callback via :3001
Fire the turn, return immediately, have the runtime POST the reply back to
`:3001`. Rejected because the runtime has no callback mechanism — it needs runtime
changes we don't own, and it duplicates what streaming already gives us.

## Decisions (resolved — Anthony, 2026-08-13)
1. **Mechanism = Option A (streaming + liveness).** Consume `/chat/stream`; not the
   `:3001` callback.
2. **Idle timeout = 90s** (`AGENT_API_IDLE_TIMEOUT`, 3× the 30s keepalive).
   Implemented as the `requests` stream **read timeout** — time-to-next-chunk —
   so any event or keepalive resets it; 90s of total silence ⇒ dead ⇒ retry.
3. **Liveness-only — no absolute ceiling.** A turn runs as long as events flow. Add
   a generous ceiling later only if we ever observe a stuck-but-keepaliving turn.
4. **Stay on `requests`** (`stream=True`) — no new dependency.

## Acceptance
- A turn that takes > 5 min but keeps emitting events **completes** (reply
  delivered), instead of becoming `failed_retryable`.
- A genuinely dead runtime (no events past the idle timeout) fails fast and
  retries per existing durable semantics.
- `session_id` rotation bookkeeping still works from the stream's `session_id`.
- No change to worker concurrency, `reply_ready` boundary, or outbound send.
- (Acceptance requires a real long turn, which only Anthony can safely trigger —
  Claude will not send test messages to James.)

## Key Files
- `gateway/gateway.py` — `call_hermes()` (~347-465): switch `_chat()` to stream
  `/chat/stream`, parse SSE, idle-timer; new `AGENT_API_IDLE_TIMEOUT` constant.
- Runtime API reference (read-only): `~/.hermes/hermes-agent/gateway/platforms/api_server.py`
  (`_handle_session_chat_stream`, keepalive const at line 68).

## Notes
- Raised by the concurrent LLM (2026-08-12) as "async turns"; research shows the
  streaming endpoint already provides the needed liveness without any callback
  plumbing.
