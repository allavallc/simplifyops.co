# Story 39 - Align AGENTS.md to the whitelabel blueprint governance rules

## Status
**Done (branch `story-39-align-agents-md`).** Final P0 story of the blueprint adoption backlog.

## Goal
Fold the blueprint's agent-governance rules into `AGENTS.md` and point at the P0 artifacts (36–38),
without duplicating the existing rules 1–11.

## What was done
- Rewrote **rule 11** to point at `product/agent-feature-dev-process.md` (exact flow) + the PROTECTED
  invariants in `product/product-decisions/current-architecture.md`, with changes recorded in
  `architecture-decisions.md`.
- Added **rules 12–15**: (12) ask-when-ambiguous + plan-whole-feature; (13) research requirement;
  (14) product operating model (decisions/stories/summaries + `sync_story_summaries.py`); (15) boundary
  contracts + agent-operable-data access levels + gitignored `ops/INFRASTRUCTURE.md`.

## Acceptance
- AGENTS.md rules 12–15 present + rule 11 updated; all referenced paths resolve; markdown-only.
- Merged to `main` after doc sanity.

## Review
Markdown-only (AGENTS.md + this story). All referenced artifacts exist (agent-feature-dev-process.md,
product-decisions/, stories-list/archive/parkinglot/proposals, sync tool, INFRASTRUCTURE.example.md).
No code touched. No 🔴. **Done.**
