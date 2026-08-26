# Story 37 - Tracked story summaries + proposals + sync tool

## Status
**In progress (branch `story-37-tracked-story-summaries`).** P0 of the blueprint adoption backlog.

## Goal
Adopt the blueprint's **Product Summaries And Proposals** model: compact tracked summary files that
are the product surface (readable without ingesting full local story files), kept in sync by a tool.

## Scope
- `scripts/sync_story_summaries.py` — `generate` (rewrite the generated block of
  `product/stories-archive.md` from `product/stories/archive/`) and `check` (validate: no duplicate
  story numbers across active+archive; archive summary in sync). `check` exits non-zero for CI.
- **Adaptation:** `product/stories-list.md` is a **curated forward-looking backlog** (includes planned
  stories 40–58 with no full files yet), so the tool **validates** it but never overwrites it — only
  `stories-archive.md` is generated. (Blueprint assumes list is generated; we keep it curated.)
- New tracked summaries: `product/stories-archive.md` (generated), `product/stories-parkinglot.md`
  (parked: Docker), `product/stories-proposals.md` (none yet; governed `proposal<N>` writes later).
- **Archive completed stories** to `product/stories/archive/`: 25, 26, 27, 28, 29, 31, 33, 35, 36.
- `tests/test_story_summaries.py` — parse + no-duplicate-numbers + generate/check invariants.

## Acceptance
- `sync_story_summaries.py check` returns 0; `generate` produces `stories-archive.md` matching the
  archive dir; 9 completed stories moved to `archive/`.
- ruff clean on the new script; the new test passes; full pytest green.
- Merged to `main` after the gate.

## Review
`sync_story_summaries.py` (generate/check) + 3 tests. Archived 9 completed stories → `archive/`;
created `stories-archive.md` (generated), `stories-parkinglot.md` (Docker), `stories-proposals.md`.
The `check` immediately caught a real pre-existing bug — duplicate `story-8` — resolved by renumbering
the legacy Google-OAuth story to **59**. Full ruff clean, pytest 9/9, `check` = OK. No 🔴. **Done.**
