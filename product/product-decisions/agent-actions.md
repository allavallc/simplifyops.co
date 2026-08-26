# Agent Action Decisions

Governed decisions about what the runtime agent (James) may **do** — action authority, approval, and
boundaries. Complements people governance (who may converse) with action governance (what may happen).

## Current position (2026-08-26)

- **Governance is database-backed** (`people` / `person_identities` in `whitelist_app`) — never
  file-based allowlists. `can_converse` gates whether James replies; `can_influence` gates whether an
  exchange may shape memory. See `current-architecture.md` → Governance.
- **Safety / action gate: pending.** There is no dedicated safety-gate / action-confirmation layer yet
  (blueprint's "safety before runtime handoff"). Sensitive external actions are not yet gated by a
  confirmation/review flow. **Known gap** — future story.
- **No runtime Settings/config mutation by the agent.** James must not mutate settings, config, MCP,
  or governance at runtime. Any such capability requires an explicit product decision + a narrow
  governed tool path (never a broad `change_anything` tool). Prefer deactivate/archive over hard delete.
- **James is off-limits for testing** — no injected messages via `POST /messages`, the Telegram bot,
  or any API/script. All interaction goes through Anthony (see CLAUDE.md / AGENTS.md).
- **Agent-operable data:** any feature exposing data the runtime agent can see/act on must declare its
  access level (none / read-only / owner-scoped write / admin-only / super-admin-only) and reuse the
  same service, validation, authorization, and audit as admin surfaces.

## Open / future
- Define the safety-gate + `agent_actions` ledger (action type, risk, recipients, confirmation
  prompt/response, status) per the blueprint. Track as a backlog story when scoped.
