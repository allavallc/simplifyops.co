# Story 36 - Establish product/product-decisions/ (durable decision home)

## Status
**In progress (branch `story-36-product-decisions-folder`).** P0 of the whitelabel-blueprint
adoption backlog (`product/stories-list.md`). Markdown-only.

## Goal
Adopt the blueprint's **Product Folder Operating Model**: durable product/architecture decisions live
under `product/product-decisions/`, not scattered in stories/handoffs/chat. This is the source-of-truth
home the blueprint's map points to first (after `AGENTS.md` + graph).

## Scope / lifecycle
Create `product/product-decisions/` with the four blueprint files, whitelabeled to simplifyops/James:
- **`current-architecture.md`** — the canonical concise current-state architecture. **Move** the
  existing canonical arch (was `ops/current-architecture.md`) here (it already holds the message flow,
  services, DB, and the PROTECTED architectural invariants). Update all references.
- **`architecture-decisions.md`** — dated decision log + rationale. Seed with this session's durable
  decisions (Jinja-not-React & retire SPA; config env-owned + per-env editor; DB-source-of-truth for
  runtime config; Hermes 0.19→0.20.5 via install.sh; gateway decomposed behind `hermes_client`;
  protected invariants 1–11; selective blueprint adoption).
- **`agent-actions.md`** — governed action decisions (seed: current governance = `people` DB, safety
  gate pending; James interaction rules; no runtime Settings mutation without a governed tool).
- **`mcp-setup-and-status.md`** — current MCP status (third-party `@dguido/google-workspace-mcp`
  wired in config.yaml, `tokens.json` missing → not authorized; repo-owned connectors are backlog
  story 55; **MCP changes need Anthony** per CLAUDE.md).

The old `ops/current-architecture.md` path becomes a one-line pointer to the new location (so old
muscle memory still lands right). `ops/james-stack-setup.md` and `ops/persistent-mcp-setup.md` stay in `ops/`.

## Reference updates
CLAUDE.md, AGENTS.md, `product/product-dev-guidelines.md`, `plan-architecture/architecture.md`,
`product/stories-list.md`, and stories 25/26/29/33 → repoint the old `ops/` path to
`product/product-decisions/current-architecture.md`.

## Acceptance
- `product/product-decisions/` exists with the 4 files; canonical architecture moved there with the
  invariants intact; no dangling `product/product-decisions/current-architecture.md` refs (pointer left in place).
- Markdown/path sanity: every referenced path resolves; no broken links.
- Merged to `main` after check (markdown-only — doc sanity, not full pytest).

## Review
Markdown-only. `product/product-decisions/` created with all 4 files; canonical architecture moved
(invariants intact); `ops/current-architecture.md` left as a pointer; all 7 referencing files
repointed; no stale refs (only this story's prose describes the old path). No code touched → doc/path
sanity only, no full pytest. No 🔴. **Done.**
