# Story 63 - Settings: honest Channels + Tools (remove UI-only shells)

## Status
**Done.** Increment of [[story-45]] — remove the last non-OAuth UI-only shells from Settings.

## Goal
Make the Channels and Tools sections tell the truth instead of showing fake disabled inputs/buttons
and placeholder `—`s (spec: "remove UI-only shells").

## Scope (template + one context tweak — no new backend)
- **Channels:** drop the fake per-channel session-cap `<input>`s, the phantom Email/Phone rows, and the
  disabled "Save channel settings" button. Show the one real channel (Telegram: Active, bot identifier,
  token presence). Note that per-channel caps + more channels are planned ([[story-54]]); session caps
  use the global default (Session health).
- **Tools:** replace the placeholder "MCP health / Active toolsets —" with a real **MCP servers:
  N enabled / M total** count sourced from the runtime config metadata already loaded for the page;
  keep the "Go to Tools" link.
- `pages.py`: `tools` context now computes MCP enabled/total from `mcp_servers` (no placeholder).

## Non-goals
- Workspace OAuth (the remaining Settings shell) — its own larger, sensitive track (overlaps
  [[story-59]]).
- Per-channel config editing / new channels — [[story-54]].

## Acceptance
- Settings shows no dead "not implemented" buttons or fake inputs in Channels/Tools; Tools shows a real
  MCP count; page renders. Full ruff + pytest green; merged.

## Review
Display-only cleanup (template + a context computation reusing already-loaded `mcp_servers`); no new
endpoints/logic → no new tests (nothing testable added; existing suite green). brooks-review/audit: n/a
for behavior — removes misleading shells, no coupling/dup. **Gate:** ruff clean; pytest 29 green; app
imports (77 routes). **Done.**
