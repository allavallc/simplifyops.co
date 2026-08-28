# Protocol — Upgrading the Hermes runtime

**Last updated: 2026-08-27** — rewritten from the generic whitelabel blueprint to **this repo's actual
stack** (`install.sh`, **no Docker**, repo-owned `simplifyops-*` systemd units). This is the master
doc for Hermes upgrades in this repo; it replaces the earlier Docker/`Dockerfile.hermes`-centric draft.

The safe, repeatable procedure for moving James's runtime (Hermes) to a new version. Hermes is an
**external dependency reached only through `gateway/hermes_client.py`** (protected rule 10) — that
adapter is the containment boundary, which is what makes upgrades a bounded operation instead of a
codebase-wide risk. Formalizes the 0.19.0 → 0.20.5 run ([[story-33]]) and the
[[hermes-upgrade-pin-workflow]] learning.

> **Runtime upgrades are governed.** Coordinate before upgrading; never bundle an upgrade with UI or
> feature changes in one gate run (upgrade + green **first**, or sequence explicitly). Do **not**
> message James to smoke-test (CLAUDE.md).

## Core principle — pin, inspect, install, test, then re-pin

**Pin the current working version first so we always know what worked and can roll back. Only advance
the "current" pin after the new version is up and the full gate passes.** The pin lives in
`product/product-decisions/current-architecture.md` (the canonical version record).

## Procedure

1. **Pin the known-good baseline.** Record the exact current version (the rollback target) and capture
   a healthy-state baseline: services active, admin `/health` 200, runtime API `:8642` up. **No James
   smoke message** — check health endpoints and `journalctl`, not the agent.
2. **Inspect the new version before installing.** Read the release notes/changelog: breaking changes,
   config-format migrations, and anything touching the codex runtime, service-file generation, or the
   config schema. Note anything that would need a runtime patch (see "Runtime patches" below).
3. **Back up** the current install and any locally-modified runtime files into a dated rollback kit
   (the 0.20.5 run used `/home/pi/hermes-upgrade-backup-<ts>/`).
4. **Install** via the **supported installer** — `install.sh`. **`pip install hermes-agent` is
   deprecated** and **`hermes update` is not the path** (it overwrote runtime files and regenerated a
   service unit — the source of the old patch churn). If the `~/.hermes/hermes-agent` checkout is
   corrupt, move it aside and let `install.sh` do a fresh clone. **Docker note:** the generic blueprint
   treats a Docker image (`Dockerfile.hermes` + `HERMES_AGENT_REF` pin) as the source of truth — **that
   does not apply here.** This repo runs Hermes natively under systemd; there is no Docker runtime.
5. **Apply runtime patches, if any.** See "Runtime patches" — as of 0.20.5 there are **none**.
6. **Verify healthy:** all services active, runtime API `:8642` reconnects (~15s), admin `/health`
   200, no restart loop (`journalctl -u simplifyops-agent-runtime -n 50 --no-pager`, `NRestarts=0`).
   Confirm the config auto-migrated cleanly (0.20.5 migrated config `v33 → v39`).
7. **Run the full gate** (below).
8. **Only when the new version is up AND the gate is green**, advance the "current" pin in
   `product/product-decisions/current-architecture.md` (and `AGENTS.md` if a known-issue step changed).
   If anything fails at 5–7, **roll back** to the pinned known-good version from the rollback kit.

## The gate to run after an upgrade

Run and record with the testing-phase readout (`… (**HERE**) …`), per CLAUDE.md:

1. **brooks-audit** (architecture) — clean, or Criticals justified. `brooks-review` too if the branch
   has a diff (an upgrade that changes no repo files has nothing to review).
2. **focused ruff** → **focused pytest** (changed areas)
3. **full ruff** (`./.venv/bin/ruff check .`) → **full pytest** — both green.

An upgrade that changes no repo files should not move ruff/pytest results; a change in results means
the upgrade altered runtime behavior the tests observe — investigate before re-pinning.

## Runtime patches

Occasionally an upstream Hermes file needs a repo-owned modification the installer does not carry
(historically: a `codex_runtime.py` `get_final_response()` `None`-backfill). The **mechanism** for any
such patch is:

- **Marker-based** — each patch brackets its change with a unique comment marker so it can be detected
  and re-applied without duplicating.
- **Idempotent** — running twice is a no-op; a patch already present is left alone.
- **Fail-closed** — if the target file/anchor is not found (upstream moved it), the patcher **errors
  and refuses to start the runtime** rather than silently leaving an unpatched, crash-looping runtime.

**Current state: there are no runtime patches.** The `codex_runtime.py` backfill was **resolved
upstream in 0.20.5** (boots clean, `NRestarts=0`), and the old `EnvironmentFile` re-add applied only
to the **legacy `hermes-gateway.service`** (pip-based, now stopped) — the current
`simplifyops-gateway.service` / `simplifyops-agent-runtime.service` units are **repo-owned** and not
regenerated by the installer. Because there are zero patches, **`scripts/apply_hermes_runtime_patches.py`
is deliberately not created yet** — an empty patch-applier would be scaffolding (CLAUDE.md: no
short-term fixes, minimal code). The first time a real patch is required, create the script to that
spec (marker-based / idempotent / fail-closed), wire it into runtime startup, add patch + layout
tests, and record the patch here.

## Rollback

1. Reinstall the pinned known-good version from the dated rollback kit.
2. `sudo systemctl daemon-reload` and restart `simplifyops-agent-runtime.service`
   (+ `simplifyops-gateway.service` if its unit changed).
3. Confirm health (step 6). Leave the "current" pin at the known-good version — never advance it on a
   failed upgrade.

## Why the blast radius is bounded

- All runtime calls go through `gateway/hermes_client.py` (protected rule 10). A changed request/
  response shape is absorbed there, not across the codebase — see
  [[modularize-external-deps-behind-interfaces]].
- The durable message workflow persists each reply (`reply_ready`) before delivery, so a runtime
  restart mid-upgrade costs a resend, never a lost or double-generated reply — see
  [`durable-message-workflow.md`](durable-message-workflow.md).
