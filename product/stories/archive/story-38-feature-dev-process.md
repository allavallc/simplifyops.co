# Story 38 - Feature-dev process doc + push-check scripts + infrastructure file

## Status
**In progress (branch `story-38-feature-dev-process`).** P0 of the blueprint adoption backlog.

## Goal
Adopt the blueprint's **Feature Development Flow** + **CI/pre-push reporting** + **Infrastructure**
rules as concrete, repo-specific tooling: one command flow, two check scripts, and a gitignored infra
inventory. Complements `product/product-dev-guidelines.md` (principles) with exact commands.

## Scope (adapted to our setup: native/systemd, no Docker, staging pending story-30)
- **`product/agent-feature-dev-process.md`** — the exact flow: branch off `main` (`story-N-<slug>`),
  gate order (Brooks-audit → focused ruff → focused pytest → full ruff → full pytest → sync check →
  commit), the `(**HERE**)` progress-line convention, merge `--no-ff`, push, delete branch,
  archive + `sync_story_summaries.py generate/check`. Mark **known gaps**: no CI yet (story 41),
  no Schemathesis (42), staging split (30).
- **`scripts/agent_pre_push_check.sh`** — full ruff + full pytest + `sync_story_summaries.py check`;
  `git fetch` + show ahead/behind vs `origin/main` and the commit list to push. Non-zero on failure.
- **`scripts/agent_post_push_check.sh <sha>`** — confirm `origin/main` contains `<sha>`; check the
  four services active + admin `/health`.
- **`ops/INFRASTRUCTURE.md`** — gitignored infra inventory (VM/IP/SSH/deploy/env). Add a tracked
  **`ops/INFRASTRUCTURE.example.md`** template; gitignore the real file.

## Acceptance
- Process doc present; both scripts executable and pass on a clean tree; `INFRASTRUCTURE.md` gitignored
  with a tracked example; full ruff + pytest green.
- Merged to `main` after the gate.

## Review
`agent-feature-dev-process.md` (command flow + progress line + known gaps), `agent_pre_push_check.sh`
(full ruff+pytest+sync+divergence) + `agent_post_push_check.sh` (sha-on-origin + services + health),
both executable. `ops/INFRASTRUCTURE.md` gitignored; `INFRASTRUCTURE.example.md` tracked. Pre-push run:
ruff clean, pytest 9/9, sync OK. No code paths changed (bash/docs). No 🔴. **Done.**
