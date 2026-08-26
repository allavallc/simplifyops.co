# MCP Setup and Status

Current MCP (Model Context Protocol) ownership, status, and decisions. **MCP changes require Anthony's
explicit guidance** (CLAUDE.md) — high mistake potential.

## Current status (2026-08-26)

- **Third-party connector in use, not repo-owned.** `config.yaml` wires
  `@dguido/google-workspace-mcp` servers. This package **self-manages OAuth** in
  `~/.hermes/profiles/simplifyops/home/.config/google-workspace-mcp/`, which **bypasses app
  governance/audit** — it conflicts with the blueprint's repo-owned-connector model.
- **Not authorized / not functional.** `credentials.json` exists but `tokens.json` is **missing** →
  never authorized → Google tools are not yet working.
- **No repo-owned `connectors/` yet.** The blueprint wants `connectors/<domain>/` with
  client → service → FastMCP server separation, injected-client tests, and short-lived tool-context
  tokens resolved via `GET /api/tool-contexts/{token}` (that token-minting path already exists in the
  gateway — `gateway/tool_context.py`).

## Decisions / direction

- **Repo-owned connectors are the target** (backlog **story 55**), replacing the third-party package,
  so tool access goes through governed, audited, typed services.
- **Deferred-tools runtime policy** (`tool_search`/`tool_describe`/`tool_call` only) is a separate
  backlog item (**story 56**).
- **Do not** build/configure/authorize/modify MCP servers or connectors without Anthony. Do not adopt
  a third-party MCP manager that bypasses the repo-owned model.
