# Story 41 - CI workflow (ruff + pytest + story-summary check)

## Status
**Done (branch `story-41-ci-workflow`).** P1 of the blueprint adoption backlog.

## Goal
Adopt the blueprint's **CI** gate so the required checks run automatically, and label the gates that
are NOT yet automated as known gaps (rather than implying enforcement).

## What was done
- `.github/workflows/ci.yml` — on push to `main` + PRs: setup Python 3.13, `pip install -r
  requirements-dev.txt` (ruff + pytest), then **ruff check .**, **pytest**, **sync_story_summaries.py
  check**. Adapted to our stack (native/systemd, no Docker; tests use only stdlib +
  `gateway.transcription`, so no web/db deps needed).
- **Known gaps documented in the workflow:** brooks-audit (agent-invoked), Schemathesis (story 42),
  live service/health checks, staging deploy verification (story 30).

## Acceptance
- Workflow present and valid; its commands (`ruff check .`, `pytest`, `sync check`) pass locally; the
  run triggers on the push to `main` and goes green. Merged to `main` after the gate.

## Review
CI runs the same 3 checks our `agent_pre_push_check.sh` runs locally. Validated the commands pass
locally (ruff clean, pytest 9/9, sync OK); the GitHub run executes on push. Uncovered gates labeled as
known gaps in the workflow header. No 🔴. **Done.**
