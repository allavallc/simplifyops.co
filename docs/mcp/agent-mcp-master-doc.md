# Boundary contract — Agent ↔ MCP tools (master doc)

The boundary between the runtime agent (Hermes) and the tools it can call via MCP. This documents the
**contract** — how a tool call is authorized, scoped to a person, and audited. It does **not** change
current MCP status or authorize any connector.

> **MCP changes require Anthony's explicit guidance** (CLAUDE.md, `AGENTS.md`). This doc is
> descriptive. For *current* MCP ownership/status/decisions see
> [`../../product/product-decisions/mcp-setup-and-status.md`](../../product/product-decisions/mcp-setup-and-status.md).

Documented per the rule-15 contract checklist. Grounded in `gateway/tool_context.py`,
`admin_api/routes/tool_contexts.py`.

## The tool-context token boundary

An MCP tool must act **as a specific person, within their authority** — not as an ambient super-user.
The mechanism is a short-lived, hashed tool-context token minted per request and resolved by the tool
at call time.

```
worker builds person context (worker.py → governance.get_person_context)
  → create_tool_context(request_id, person_ctx, authority, channel, from_id, can_influence)
        stores sha256(token) + scope in tool_contexts, TTL 30 min
        returns raw token (never persisted) into the runtime handoff
  → MCP tool receives the raw token
  → GET /api/tool-contexts/{token}   [admin_api/routes/tool_contexts.py]
        resolves scope: request_id, person_id, authority, primary_email, timezone, can_influence
  → tool executes scoped to that person, then audit
```

## Contract: tool-context mint + resolve

| Field | Value |
|---|---|
| Caller / callee | mint: worker → `gateway/tool_context.create_tool_context`. resolve: MCP tool → `GET /api/tool-contexts/{token}` |
| Route | `GET /api/tool-contexts/{token}` (admin control plane, :3000) |
| In schema | mint: `request_id`, `person_ctx`, `authority`, `channel`, `from_id`, `can_influence`. resolve: raw `token` (path) |
| Out schema | resolve: `{request_id, person_id, authority, channel, from_id, primary_email, timezone, can_influence, expires_at}` or `404 tool_context_not_found_or_expired` |
| Persisted state | `tool_contexts` row — **only** `sha256(token)` (`token_hash`) + scope + `expires_at`. The raw token is never stored. |
| `request_id` | Carried from the originating message; ties every tool call back to the durable workflow |
| Idempotency | Resolve is read-only (no state change) — safe to call repeatedly within TTL |
| Timeout / TTL | `TOOL_CONTEXT_TTL_MINUTES = 30`; expired tokens resolve to `404` (`expires_at > now()` enforced in SQL) |
| Credential owner | The token is a bearer capability; the admin API owns validation. Provider OAuth (e.g. Google) is a **separate** credential owned by the connector, not carried in the token. |
| Delivery owner | n/a |
| Status mapping | valid+unexpired→`200` scope; unknown/expired→`404` |
| Audit fields | tool actions must audit against `request_id` + `person_id` (same `log_audit` path as admin surfaces) |
| Redaction | raw token never logged or stored; only `token_hash` persists |

## Authority & access rules (rule 15)

- A tool acts **owner-scoped** by default — it sees/acts only within the resolved `person_id` and
  `authority`. `can_influence=false` senders must not trigger state-changing tools.
- No broad `change_anything` tool. Tools reuse the same service + validation + authz + audit as the
  admin surfaces; prefer deactivate/archive over hard delete.
- Any data the agent can see/act on declares an access level (none / read-only / owner-scoped /
  admin / super-admin) and enforces it at the service, not just the UI.

## Target model (not yet built — backlog)

The blueprint's repo-owned model (backlog **story 55**) is `connectors/<domain>/` with
**client → service → FastMCP server** separation and injected-client tests, replacing the current
third-party `@dguido/google-workspace-mcp` (which self-manages OAuth and bypasses governance/audit —
see the status doc). A **deferred-tools runtime policy** (`tool_search` / `tool_describe` /
`tool_call` only) is **story 56**.

## Invariants (do not break without an approved story)

- Tools are scoped through a **resolved tool-context token**, never ambient credentials.
- Only `sha256(token)` + scope is persisted; the raw token lives only in the request handoff.
- Tool actions reuse the governed service + audit path — the runtime does not get a privileged
  side-channel around governance (protected rules 1 & 9).
- No MCP server/connector is built, configured, or authorized without Anthony.
