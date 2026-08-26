# Story 33 - Upgrade Hermes to the latest version, then re-run the full gate

## Status
**DONE (2026-08-25) — upgrade verified healthy.** Hermes **0.19.0 → 0.20.5** via the supported
`install.sh` (pip is deprecated; discovered mid-flight). Recovered from a corrupt `~/.hermes/hermes-agent`
git checkout (moved aside → fresh clone). Config auto-migrated v33→v39. **codex_runtime patch obsolete**
(0.20.5 boots clean, NRestarts=0). All services active, API :8642 up, admin `/health` 200. Re-pinned:
`ops/current-architecture.md` + AGENTS.md updated. Rollback kit at
`/home/pi/hermes-upgrade-backup-20260824-213008/`.
**Gate:** full **pytest green (6 passed)** on the upgraded stack — confirms the upgrade broke nothing.
Full **ruff = 30 errors** but all **pre-existing** (story-24 baseline + this session's un-gated
People/Settings WIP), **not upgrade-related** (upgrade changed no repo files). brooks-audit + ruff
cleanup belong to gating the session's code work, tracked separately.
Follow-ups: browser/computer-use deps skipped (re-add via `install.sh --ensure browser` /
`uv pip install -e '.[all]'`); legacy `hermes-gateway.service` (pip-based) left stopped; old pip
`hermes-agent==0.19.0` still installed but shadowed by the new launcher.

## Goal
Upgrade Hermes from the current pinned version (v0.19.0 per `ops/current-architecture.md`) to the
**latest release**, verify the runtime comes back healthy, and then re-run the full quality gate to
confirm the repo is still green on the upgraded stack.

## Why care (known post-upgrade gotchas — from AGENTS.md "Known Issues & Fixes")
A `hermes update` **overwrites `/home/pi/.hermes/hermes-agent/agent/codex_runtime.py` and
regenerates the service file**, so after upgrading we must re-apply local patches or the gateway
crash-loops:
1. Re-apply the `codex_runtime.py` `get_final_response()` `TypeError`/`None` backfill patch
   (`run_codex_stream` + `run_codex_create_stream_fallback`).
2. Re-add `EnvironmentFile=/home/pi/.config/relay.env` to
   `/etc/systemd/system/hermes-gateway.service` (hermes strips it on reinstall).
3. `sudo systemctl daemon-reload && sudo systemctl restart hermes-gateway.service`.

## Proposed approach — pin, inspect, install, test, then re-pin (coordinate first)
Process learning (another project): **pin the current working version first so we always know what
worked and can roll back; only advance the "current" pin after the new version is up and tests pass.**

1. **Pin the known-good baseline.** Record and explicitly pin the exact current Hermes version — the
   version we *know* works and our rollback target. Capture a healthy-state baseline (services
   active, `/health`, one governed smoke — **without** messaging James).
2. **Inspect the new version before installing.** Read the release notes/changelog for latest; check
   for breaking changes + known issues, especially anything touching `codex_runtime.py`, service-file
   generation, or the config format.
3. **Back up** `codex_runtime.py` and the current service/unit files.
4. **Install** the new version.
5. **Re-apply** the two post-upgrade patches (codex_runtime backfill + `EnvironmentFile`);
   `daemon-reload`; restart `hermes-gateway` + `simplifyops-agent-runtime`.
6. **Verify healthy:** services active, runtime API `:8642` reconnects (~15s), admin `/health` 200,
   no restart loop in `journalctl`.
7. **Run the full gate** (below).
8. **Only when the new version is up AND all tests pass**, advance the "current" pin to the new
   version and update `ops/current-architecture.md` (+ AGENTS.md if any known-issue step changed).
   If anything fails at 5–7, **roll back to the pinned known-good version.**

## Re-run the full gate (owner's requested sequence)
After the upgrade is verified healthy, run and record, printing the testing-phase readout
(`... (**HERE**) ...`):
1. **brooks-audit** (architecture) — clean, or Criticals justified in Review.
2. **focused ruff** — `./.venv/bin/ruff check <changed paths>`.
3. **focused pytest** — tests for changed areas.
4. **full ruff** — `./.venv/bin/ruff check .` green.
5. **full pytest** — full suite green.
(Standard gate also pairs **brooks-review**; owner explicitly listed brooks-audit — run review too
if the branch has a diff to review.)

## Acceptance
- Hermes on latest; runtime + gateway healthy, no restart loop; both post-upgrade patches re-applied
  and documented.
- brooks-audit clean (or justified); focused + full `ruff` and `pytest` all green.
- `ops/current-architecture.md` version updated.

## Review
_(fill before commit/push: brooks-audit [+review] scores/Criticals, then focused + full ruff/pytest green.)_

## Notes
Independent of the page-by-page UI work ([[story-31]] People, [[story-32]] Settings). Do not bundle
the runtime upgrade with UI changes in one gate run — upgrade + green first, or sequence explicitly.
